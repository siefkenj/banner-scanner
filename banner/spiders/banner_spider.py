# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider, Request
from scrapy.selector import HtmlXPathSelector
from scrapy.log import DEBUG
import re

from banner.items import BannerItem

class BannerSpider(BaseSpider):
    name = 'banner'
    allowed_domains = ['www.uvic.ca','web.uvic.ca']
    start_urls = ['https://www.uvic.ca/BAN2P/bwckschd.p_disp_dyn_sched']
    schedule_url_template = 'https://www.uvic.ca/BAN2P/bwckschd.p_get_crse_unsec?term_in={term}&sel_subj=dummy&sel_day=dummy&sel_schd=dummy&sel_insm=dummy&sel_camp=dummy&sel_levl=dummy&sel_sess=dummy&sel_instr=dummy&sel_ptrm=dummy&sel_attr=dummy&sel_subj={subject}&sel_crse={number}&sel_title=&sel_schd=%25&sel_insm=%25&sel_from_cred=&sel_to_cred=&sel_camp=%25&sel_levl=%25&sel_ptrm=%25&sel_instr=%25&begin_hh=0&begin_mi=0&begin_ap=a&end_hh=0&end_mi=0&end_ap=a'
    classlist_url_template = 'https://www.uvic.ca/BAN2P/bwckctlg.p_display_courses?term_in={term}&sel_subj=dummy&sel_levl=dummy&sel_schd=dummy&sel_coll=dummy&sel_divs=dummy&sel_dept=dummy&sel_attr=dummy&sel_subj={subject}'
    calendar_url_template = 'http://web.uvic.ca/calendar/CDs/{subject}/{number}.html'
    
    def __init__(self):
        BaseSpider.__init__(self)

    
    def parse(self,response):
        """
        Parses only the first page of the dynamic class catalog. 
        
        Extracts the available terms from the select box and generates 
        requests for the search pages for each term. These requests are handled
        by the parse_term method
        """
        hxs = HtmlXPathSelector(response)
        
        # get term dates from the options in a select box
        terms = hxs.select('//select[@id="term_input_id"]/child::option').select('@value').extract() 
        
        # eliminate the entry corresponding to None
        terms = [t for t in terms if len(t) > 0]
        
        self.log('Got terms: '+str(terms))
        
        for term in terms:
            term_url = 'https://www.uvic.ca/BAN2P/bwckgens.p_proc_term_date?p_calling_proc=bwckschd.p_disp_dyn_sched&p_term='+term
            request = Request(term_url,callback=self.parse_term)
            request.meta['term'] = term
            yield request
            
    def parse_term(self,response):
        """
        Parses the search page for a particular term.
        
        Extracts the subject list from the first select box and generates
        requests for the classlist for each subject in the current term. These
        requests are handled by the parse_courses callback.
        """
        hxs = HtmlXPathSelector(response)
        subjects = hxs.select('//select[@id="subj_id"]/child::option').select('@value').extract()
#        self.log('Got subjects; '+str(subjects))
        
        for subj in subjects:
            subj_url = self.classlist_url_template.format(term=response.meta['term'],
                                                          subject=subj)
            request = Request(subj_url,callback=self.parse_courses)
            request.meta['term'] = response.meta['term']
            yield request
            
    def parse_courses(self,response):
        """
        Parses the classlist for a specific subject and term.
        
        Selects the links for each class details page, and uses them to fill in
        the 'url', 'number', 'department', and 'title' fields for each class
        item. Generates requests to each link in order to get pre-requisites, 
        These requests are handled by the parse_details callback.
        """
        hxs = HtmlXPathSelector(response)
        courses = hxs.select('//td[@class="nttitle"]/a')
        for c in courses:
            item = BannerItem()

            url = c.select('@href').extract()[0]
            data = dict(e.split('=') for e in url.split('?')[1].split('&'))
            desc = c.select('text()').extract()[0].split(' - ')[1].strip()
            item['url'] = url
            item['number'] = data['crse_numb_in']
            item['department'] = data['subj_code_in']
            item['title'] = desc
            item['term'] = response.meta['term']
            item['desc'] = ''
            item['crn'] = ''
            item['enrollment'] = ()

            request = Request("https://www.uvic.ca" + url, callback=self.parse_details)
            request.meta['item'] = item

            yield request
            
    def parse_details(self, response):
        """
        Parse class prerequisites.
        """
        hxs = HtmlXPathSelector(response)
        prereqs = hxs.select("//span[text()='Faculty']/following-sibling::text() | //span[text()='Faculty']/following-sibling::a")
        prereqs = self.parse_prereqs(prereqs)
        
        item = response.meta['item']
        item['prereqs'] = prereqs
        
        calendar_url = self.calendar_url_template.format(subject=item['department'],
                                                         number=item['number'])
        request = Request(calendar_url,callback=self.parse_calendar)
        request.meta['item'] = item
        request.meta['handle_httpstatus_list'] = [404]
        return request
        
#        # next stop is the schedule page
#        schedule_url = self.schedule_url_template.format(term=item['term'],
#                                                         subject=item['department'],
#                                                         number=item['number'])
#        request = Request(schedule_url,callback=self.parse_schedule)
#        request.meta['item'] = item                                                
#        return request
        
    def parse_calendar(self,response):
        """
        Parse the calendar page for the class description and send the class
        data item out on the pipeline.
        
        Afterwards, request the schedule page for the class and term
        """
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
        first_p = hxs.select('//div[@id="CDpage"]/p[1]')
        has_b_child = len(first_p.select('b')) > 0
        
        if not has_b_child:
            description = first_p.select('text()').extract()
        else:
            description = ''
        
        # if we have reached a valid calendar page, then the above XPath
        # selection returns a list with a single element, if we get a 404,
        # the selection returns empty
        if len(description) > 0:
            item['desc'] = description[0]
        else:
            item['desc'] = ''
        
        # next stop is the schedule page
        schedule_url = self.schedule_url_template.format(term=item['term'],
                                                         subject=item['department'],
                                                         number=item['number'])
        request = Request(schedule_url,callback=self.parse_schedule)
        request.meta['item'] = item                                                
        return request
        
    def parse_schedule(self,response):
        """
        Parse the schedule for a class and term 

        Grab all the links for each section to get CRNs and enrollment info               
        """
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
        links = hxs.select('//th[@class="ddtitle"]/a/@href').extract()
        
        if len(links) > 0:
            for l in links:
                url = 'https://www.uvic.ca'+l
                request = Request(url,callback=self.parse_section)            
                request.meta['item'] = item
                yield request
        else:
            # no schedule info found, send the item out the pipeline
            yield item
        
    def parse_section(self,response):
        hxs = HtmlXPathSelector(response)
        title_line = hxs.select('//th[@class="ddlabel"]/text()').extract()[0]
        tokens = title_line.split('-')
        crn = tokens[1].strip()
        
        enrollment_selector = '//table//table[@class="datadisplaytable"]//th[@class="ddlabel"]/following-sibling::td/text()'
        capacity,enrolled = hxs.select(enrollment_selector)[0:2].extract()
        
        item = response.meta['item']
        item['crn'] = crn
        item['enrollment'] = (capacity,enrolled)
        return item
        
        
    def parse_prereqs(self, prereqs):
        # let's tokenize this bad boy.  All that's important in
        # text nodes is and, or, and ().  Keep the class info of the element nodes
        
        parensplit = re.compile(r'\(|\)| and | or ')
        
        def gen_prereq_group(operator, members=None):
            if members is None:
                members = []
            return {'op': operator, 'data': members}

        # turns a list of strings into a nested list based on paren tokens
        def listify(l, start=0):
            ret = []
            i = start
            while i < len(l):
                if l[i] == '(':
                    group, i = listify(l, start=i+1)
                    ret.append(group)
                elif l[i] == ')':
                    return ret, i+1
                else:
                    ret.append(l[i])
                    i += 1
                    
            # first and last elements should not be 'and' or 'or'
            if len(ret) > 0:
                while ret[0] == 'and' or ret[0] == 'or':
                    del ret[0]
                while ret[-1] == 'and' or ret[-1] == 'or':
                    del ret[-1]
        
            return ret

        # turns a list with infix 'and' and 'or' into a PrereqGroup tree
        def deinfix(l):
            if len(l) == 1:
                # normally, a single-element list is a single course, but the
                # situation may arise that we have a single nested list
                if type(l[0]) == dict:
                    return gen_prereq_group('and', [l[0]])
                else:
                    return deinfix(l[0])
            if len(l) < 1:
                return None

            items = []
            operator = l[1]

            for i in range(0, len(l), 2):
                item = l[i]
                if type(item) == list:
                    items.append(deinfix(item))
                else:
                    items.append(item)
            return gen_prereq_group(operator, items)

        parsed = []
        for elm in prereqs:
            if elm.xmlNode.type == 'text':
                parsed += [i.strip() for i in parensplit.findall(elm.extract())]
            else:
                # if we made it here, we must be an anchor element, so parse our href string and return the appropriate course
                item = self.gen_course_from_prereq_link(elm)
                if len(item['number']) > 0 and len(item['department']) > 0:
                    parsed.append(self.gen_course_from_prereq_link(elm))
                    
#        self.log('parsed = '+str(parsed),level=DEBUG)

        # we have a list of tokens, some of which are parens.  Turn this into
        # a nested list so we can continue parsing
        listified = listify(parsed)
        
        # turn our list into a tree with prefix operators instead of infix
        tree = deinfix(listified)
    
        return tree

    def gen_course_from_prereq_link(self, elm):
        item = {}

        url = elm.select('@href').extract()[0]
        data = dict(e.split('=') for e in url.split('?')[1].split('&'))
        #item['url'] = url
        item['number'] = data['sel_crse_strt']
        item['department'] = data['one_subj']

        return item
        
            
        
        
    
