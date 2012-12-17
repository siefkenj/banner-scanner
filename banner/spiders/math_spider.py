import re
from scrapy.spider import BaseSpider, Request
from scrapy.selector import HtmlXPathSelector

from banner.items import Course

class PrereqSpider(BaseSpider):
    name = "prereq"
    allowed_domains = ["www.uvic.ca"]
    start_urls = [
        "https://www.uvic.ca/BAN2P/bwckctlg.p_disp_course_detail?cat_term_in=201301&subj_code_in=MATH&crse_numb_in=342"
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        prereqs = hxs.select("//span[text()='Faculty']/following-sibling::text() | //span[text()='Faculty']/following-sibling::a")
        #self.parse_prereqs(prereqs)
        print self.parse_prereqs(prereqs)

    def parse_prereqs(self, prereqs):
        # let's tokenize this bad boy.  All that's important in
        # text nodes is and, or, and ().  Keep the class info of the element nodes
        
        parensplit = re.compile(r'\(|\)| and | or ')

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
            return ret

        # turns a list with infix 'and' and 'or' into a PrereqGroup tree
        def deinfix(l):
            if len(l) == 1:
                return gen_prereq_group('and', [l[0]])
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
                parsed.append(self.gen_course_from_prereq_link(elm))

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


#class MathSpider(BaseSpider):
class MathSpider(PrereqSpider):
    name = "math"
    allowed_domains = ["www.uvic.ca"]
    start_urls = [
        "https://www.uvic.ca/BAN2P/bwckctlg.p_display_courses?term_in=201301&sel_subj=dummy&sel_levl=dummy&sel_schd=dummy&sel_coll=dummy&sel_divs=dummy&sel_dept=dummy&sel_attr=dummy&sel_subj=CSC"
    ]

    def parse(self, response):
        #items = []
        hxs = HtmlXPathSelector(response)
        courses = hxs.select('//td[@class="nttitle"]/a')
        for c in courses:
            item = Course()

            url = c.select('@href').extract()[0]
            data = dict(e.split('=') for e in url.split('?')[1].split('&'))
            desc = c.select('text()').extract()[0].split(' - ')[1].strip()
            item['url'] = url
            item['number'] = data['crse_numb_in']
            item['department'] = data['subj_code_in']
            item['desc'] = desc

            request = Request("https://www.uvic.ca" + url, callback=self.parse_details)
            request.meta['item'] = item

            yield request
            #items.append(item)
            
        #return items
    def parse_details(self, response):
        hxs = HtmlXPathSelector(response)
        prereqs = hxs.select("//span[text()='Faculty']/following-sibling::text() | //span[text()='Faculty']/following-sibling::a")
        prereqs = self.parse_prereqs(prereqs)
        
        item = response.meta['item']
        item['prereqs'] = prereqs
        return item


def gen_prereq_group(operator, members=None):
    if members is None:
        members = []
    return {'op': operator, 'data': members}

class PrereqGroup(object):
    def __init__(self, operator, members=None):
        if members is None:
            members = []
        self.type = operator
        self.members = members
    def __str__(self):
        return "{" + "'op': '{0}', 'data': [{1}])".format(self.type, ', '.join(str(i) for i in self.members))
    def __repr__(self):
        return self.__str__()
