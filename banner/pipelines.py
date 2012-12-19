# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/topics/item-pipeline.html

import json

from scrapy.contrib.exporter import JsonItemExporter
from scrapy import log
from banner.items import Course

class BannerPipeline(object):
    def __init__(self):
        self.items = []
        self.subjects = []
        log.start()
        
        
    def close_spider(self,spider):
        log.msg('Exporting scraped data...',level=log.DEBUG)
        for subj in self.subjects:
            log.msg(subj,level=log.DEBUG)
            outfile = open(subj+'.json','w')
            exporter = JsonItemExporter(outfile)
            exporter.start_exporting()
            classes = [i for i in self.items if i['department']==subj]
            for c in classes:
                exporter.export_item(c)
            exporter.finish_exporting()
            outfile.close()

    def process_item(self, item, spider):
        """
        Add or update a course to the list of items to be exported
        """      
        for i in self.items:
            if i == item:
                # course already exists in the list, update the enrollment info
                term = item['term']
                crn = item['crn']
                if len(crn) > 0:
                    if term in i['sections']:
                        i['sections'][term][crn] = item['enrollment']
                    else:
                        i['sections'][term] = {crn:item['enrollment']}
                return item
        
        # course not found in list, create new entry
        new_item = Course()
        new_item['department'] = item['department']
        new_item['number'] = item['number']
        new_item['url'] = item['url']
        new_item['title'] = item['title']
        new_item['desc'] = item['desc']
        new_item['prereqs'] = item['prereqs']
        if len(item['crn']) > 0:
            new_item['sections'] = {item['term']:{item['crn']:item['enrollment']}}
        else:
            new_item['sections'] = {}
        self.items.append(new_item)
        if item['department'] not in self.subjects:
            self.subjects.append(item['department'])
        return item
