# -*- coding: utf-8 -*-
import re
from datetime import datetime

from scrapy.spider import BaseSpider, Request
from scrapy.selector import HtmlXPathSelector
from scrapy.log import DEBUG

from banner.items import CalendarItem, CatalogItem, ScheduleItem

TEST_SUBJECTS = ['MATH']
TEST_RUN = False

class BannerSpider(BaseSpider):
    name = 'banner'
    allowed_domains = ['www.uvic.ca','web.uvic.ca']
    start_urls = ['https://www.uvic.ca/BAN2P/bwckschd.p_disp_dyn_sched']
    schedule_url_template = 'https://www.uvic.ca/BAN2P/bwckschd.p_get_crse_unsec?term_in={term}&sel_subj=dummy&sel_day=dummy&sel_schd=dummy&sel_insm=dummy&sel_camp=dummy&sel_levl=dummy&sel_sess=dummy&sel_instr=dummy&sel_ptrm=dummy&sel_attr=dummy&sel_subj={subject}&sel_crse={number}&sel_title=&sel_schd=%25&sel_insm=%25&sel_from_cred=&sel_to_cred=&sel_camp=%25&sel_levl=%25&sel_ptrm=%25&sel_instr=%25&begin_hh=0&begin_mi=0&begin_ap=a&end_hh=0&end_mi=0&end_ap=a'
    #classlist_url_template = 'https://www.uvic.ca/BAN2P/bwckctlg.p_display_courses?term_in={term}&sel_subj=dummy&sel_levl=dummy&sel_schd=dummy&sel_coll=dummy&sel_divs=dummy&sel_dept=dummy&sel_attr=dummy&sel_subj={subject}'
    classlist_url_template = 'https://www.uvic.ca/BAN2P/bwckctlg.p_display_courses?term_in={term}&sel_subj=dummy&sel_levl=dummy&sel_schd=dummy&sel_coll=dummy&sel_divs=dummy&sel_dept=dummy&sel_attr=dummy'
    calendar_url_template = 'http://web.uvic.ca/calendar/CDs/{subject}/{number}.html'
    
    terms = []
    subjects = []
    
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
        
        # eliminate the entry corresponding to None, and remove terms that are
        # too old
        def is_valid_term(term):
            current_year = datetime.now().year
            if len(term) == 0:
                return False
            elif (current_year - int(term[0:4])) > 4:
                return False
            else:
                return True
                
        terms = [t for t in terms if is_valid_term(t)]
        
        self.log('Got terms: '+str(terms))        
        self.terms = terms
        
        # get the complete class listings
        url = self.classlist_url_template.format(term = self.terms[0])
        request = Request(url,callback=self.parse_classlist_search)
        yield request
        
        # get the schedule pages for each term and subject
#        for term in self.terms:
#            for subject in self.subjects:
#                url = self.schedule_url_template.format(term=term,subject=subject,number='')
#                item = ScheduleItem()
#                item['term'] = term
#                item['subject'] = subject
#                request = Request(url,callback=self.parse_schedule)
#                request.meta['item'] = item
#                yield request

        for term in terms:
            term_url = 'https://www.uvic.ca/BAN2P/bwckgens.p_proc_term_date?p_calling_proc=bwckschd.p_disp_dyn_sched&p_term='+term
            request = Request(term_url,callback=self.parse_term)
            request.meta['term'] = term
            yield request
            
    def parse_classlist_search(self,response):
        hxs = HtmlXPathSelector(response)
        
        if not TEST_RUN:
            subjects = hxs.select('//select[@name="sel_subj"]/option/@value').extract()   
        else:
            subjects = TEST_SUBJECTS

        # using the subjects scraped from the select element, form a url with
        # POST data to request a listing of all classes  
        url = self.classlist_url_template.format(term=self.terms[0])
        for s in subjects:
            url += '&sel_subj={0}'.format(s)
        request = Request(url,callback=self.parse_courses)
        return request
            
    def parse_term(self,response):
        """
        Parses the schedule search page for a particular term.
        
        Extracts the subject list from the first select box and generates
        requests for the schedule for each subject in the current term. These
        requests are handled by the parse_schedule callback.
        """
        hxs = HtmlXPathSelector(response)
        if not TEST_RUN:
            subjects = hxs.select('//select[@id="subj_id"]/child::option').select('@value').extract()
        else:
            subjects = TEST_SUBJECTS
        term = response.meta['term']
#        self.log('Got subjects; '+str(subjects))        
        
        for subj in subjects:
            url = self.schedule_url_template.format(term=term,subject=subj,number='')
            item = ScheduleItem()
            item['term'] = term
            item['subject'] = subj
            request = Request(url,callback=self.parse_schedule)
            request.meta['item'] = item
            yield request
            
    def parse_courses(self,response):
        """
        Parses the classlist for a specific subject and term.
        
        Selects the links for each class details page, and uses them to fill in
        the 'url', 'number', 'subject', and 'title' fields for each class
        item. Generates requests to each link in order to get pre-requisites, 
        These requests are handled by the parse_details callback.
        """
        hxs = HtmlXPathSelector(response)
        courses = hxs.select('//td[@class="nttitle"]/a')
        for c in courses:
            item = CatalogItem()

            url = c.select('@href').extract()[0]
            data = dict(e.split('=') for e in url.split('?')[1].split('&'))
            title = c.select('text()').extract()[0].split(' - ')[1].strip()
            item['url'] = url
            item['number'] = data['crse_numb_in']
            item['subject'] = data['subj_code_in']
            item['title'] = title
            request = Request("https://www.uvic.ca" + url, callback=self.parse_details)
            request.meta['item'] = item

            yield request
            
    def parse_details(self, response):
        """
        Parse class prerequisites.
        """
        hxs = HtmlXPathSelector(response)
        prereqs = hxs.select("//span[text()='Faculty']/following-sibling::text() | //span[text()='Faculty']/following-sibling::a")
        self.log("parsing "+response.url,level=DEBUG)
        self.log('prereqs = '+str(prereqs),level = DEBUG)
        prereqs = self.parse_prereqs(prereqs)
        self.log('parsed prereqs = '+str(prereqs),level = DEBUG)
        
        item = response.meta['item']
        item['prereqs'] = prereqs
        
        yield item
        
        calendar_url = self.calendar_url_template.format(subject=item['subject'],
                                                         number=item['number'])
        request = Request(calendar_url,callback=self.parse_calendar)
        request.meta['handle_httpstatus_list'] = [404]
        request.meta['subject'] = item['subject']
        request.meta['number'] = item['number']
        yield request
        
#        # next stop is the schedule page
#        schedule_url = self.schedule_url_template.format(term=item['term'],
#                                                         subject=item['subject'],
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
        item = CalendarItem()
        item['subject'] = response.meta['subject']
        item['number'] = response.meta['number']
        item['url'] = response.url
        first_p = hxs.select('//div[@id="CDpage"]/p[1]')
        has_b_child = len(first_p.select('b')) > 0
        if not has_b_child:
            description = ''.join(first_p.select('.//text()').extract())
        else:
            description = ''
        
        # if we have reached a valid calendar page, then the above XPath
        # selection returns a good description, if we get a 404,
        # the selection returns empty
        if len(description) > 0:
            item['description'] = description
        else:
            item['description'] = ''                                           
        return item
        
    def parse_schedule(self,response):
        """
        Parse the schedule for a subject and term 

        Grab all the links for each section to get CRNs and enrollment info               
        """
        hxs = HtmlXPathSelector(response)
        links = hxs.select('//th[@class="ddtitle"]/a/@href').extract()

        for l in links:
            url = 'https://www.uvic.ca'+l
            request = Request(url,callback=self.parse_section)      
            request.meta['item'] = response.meta['item']
            yield request
        
    def parse_section(self,response):
        hxs = HtmlXPathSelector(response)
        title_line = hxs.select('//th[@class="ddlabel"]/text()').extract()[0]
        tokens = title_line.split(' - ')
        crn = tokens[-3].strip()
        number = tokens[-2].split(' ')[1].strip()
        
        enrollment_selector = '//table//table[@class="datadisplaytable"]//th[@class="ddlabel"]/following-sibling::td/text()'
        capacity,enrolled = hxs.select(enrollment_selector)[0:2].extract()
        
        item = response.meta['item']
        item['number'] = number
        item['crn'] = crn
        item['capacity'] = int(capacity)
        item['enrollment'] = int(enrolled)
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
                    
            # list should not consist of exclusively 'and' and 'or'
            if all([t == 'or' or t == 'and' for t in ret]):
                return []
            
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
            # scrapy selectors no longer have the xmlNode attribute...so let's just look to see if we have an href
            # in order to tell if we're a link
            if elm.select('@href'):
                # if we made it here, we must be an anchor element, so parse our href string and return the appropriate course
                item = self.gen_course_from_prereq_link(elm)
                if len(item['number']) > 0 and len(item['subject']) > 0:
                    parsed.append(item)
            else:
                parsed += [i.strip() for i in parensplit.findall(elm.extract())]

                    
        self.log('parsed = '+str(parsed),level=DEBUG)

        # we have a list of tokens, some of which are parens.  Turn this into
        # a nested list so we can continue parsing
        listified = listify(parsed)
        
        self.log('listified = '+str(listified),level=DEBUG)
        
        # turn our list into a tree with prefix operators instead of infix
        tree = deinfix(listified)
        
        self.log('tree = '+str(tree),level=DEBUG)
    
        return tree

    def gen_course_from_prereq_link(self, elm):
        item = {}

        url = elm.select('@href').extract()[0]
        data = dict(e.split('=') for e in url.split('?')[1].split('&'))
        #item['url'] = url
        item['number'] = data['sel_crse_strt']
        item['subject'] = data['one_subj']

        return item
        
            
        
        
    
