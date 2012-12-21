# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/topics/item-pipeline.html

import json
import pickle

from scrapy.contrib.exporter import JsonItemExporter, PickleItemExporter, PprintItemExporter
from scrapy import log
from banner.items import Course, CalendarItem, CatalogItem, ScheduleItem

class BannerPipeline(object):
    def __init__(self):
        self.scraped_items = {}
        self.subjects = []
        log.start()
        
        
    def close_spider(self,spider):
        outfile_pkl = open('scraped.pkl','w')
        pickle.dump(self.scraped_items,outfile_pkl)
        outfile_pkl.close()
        log.msg('Exporting scraped data...',level=log.DEBUG)
        for subject,courses in self.scraped_items.items():
            log.msg(subject,level=log.DEBUG)
            outfile = open(subject+'.json','w')
            exporter = JsonItemExporter(outfile)
            exporter.start_exporting()
            
            to_export = []
            log.msg(str(courses),level=log.DEBUG)
            for number,items in courses.items():
                consolidated = self.consolidate_course(items)
                if consolidated is not None:
                    to_export.append(consolidated)

            # sort classes by number
            class_key = lambda x : int(x['number'][0:3])
            to_export.sort(key=class_key)                
            
            for item in to_export:
                exporter.export_item(item)

            exporter.finish_exporting()
            outfile.close()

    def process_item(self, scraped_item, spider):
        """
        Add or update a course to the list of items to be exported
        """  
        item = dict(scraped_item)
        subject = item['subject']
        number = item['number']
        if not self.scraped_items.has_key(subject):
            self.scraped_items[subject] = {number:[item]}
        elif not self.scraped_items[subject].has_key(number):
            self.scraped_items[subject][number] = [item]
        else:
            self.scraped_items[subject][number].append(item)
            
        return item
#        for i in self.items:
#            if i == item:
#                # course already exists in the list, update the enrollment info
#                term = item['term']
#                crn = item['crn']
#                if len(crn) > 0:
#                    # item contains section data
#                    enrollment = item['enrollment']
#                    capacity = item['capacity']
#                    section_dict = {'crn':crn,'enrollment':enrollment,'capacity':capacity}
#                    for t in i['terms_offered']:
#                        if term == t['term']:
#                            t['sections'].append(section_dict)
#                            return item
#                    # term not in list, make a new element
#                    i['terms_offered'].append({'term':term,'sections':[section_dict]})
#                    return item       
#                # no section data, just return
#                else:
#                    return item
#        
#        # course not found in list, create new entry
#        new_item = Course()
#        new_item['subject'] = item['subject']
#        new_item['number'] = item['number']
#        new_item['url'] = item['url']
#        new_item['title'] = item['title']
#        new_item['desc'] = item['desc']
#        new_item['prereqs'] = item['prereqs']
#        if len(item['crn']) > 0:
#            new_item['terms_offered'] = [{'term':item['term'],'sections':[{'crn':item['crn'],'capacity':item['capacity'],'enrollment':item['enrollment']}]}]
#        else:
#            new_item['terms_offered'] = []
#        self.items.append(new_item)
#        if item['subject'] not in self.subjects:
#            self.subjects.append(item['subject'])
#        return item

    def consolidate_course(self,items):
        log.msg('items: '+str(items),level=log.DEBUG)
        course = Course()
        calendar_item = None
        catalog_item = None
        schedule_items = []
        for i in items:
            if i.has_key('description'):
                calendar_item = i
            elif i.has_key('prereqs'):
                catalog_item = i
            elif i.has_key('crn'):
                schedule_items.append(i)
            else:
                raise ValueError,('Unknown item type for '+str(i))
                
        if catalog_item is None:
            log.msg('No CatalogItem found for '+str(items),level=log.DEBUG)
            return
        else:
            course['subject'] = catalog_item['subject']
            course['number'] = catalog_item['number']
            course['title'] = catalog_item['title']
            course['catalog_url'] = catalog_item['url']
            course['prereqs'] = catalog_item['prereqs']
            course['terms_offered'] = {}
            
            if calendar_item is not None:
                course['description'] = calendar_item['description']
                course['calendar_url'] = calendar_item['url']
                
            for section in schedule_items:
                term = section['term']
                crn = section['crn']
                enrollment = section['enrollment']
                capacity = section['capacity']
                section_dict = {'crn':crn,'enrollment':enrollment,'capacity':capacity}
                if not course['terms_offered'].has_key(term):
                    course['terms_offered'][term] = [section_dict]
                else:
                    course['terms_offered'][term].append(section_dict)
                    
        return course
   
