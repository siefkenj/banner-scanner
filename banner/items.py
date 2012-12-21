# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class CalendarItem(Item):
    """
    Item containing data scraped from the calendar website
    """
    number = Field()
    subject = Field()
    url = Field()
    description = Field()

class CatalogItem(Item):
    """
    Data structure received from scraper
    
    Contains a single section of a particular class in a specific term
    """
    number = Field()
    subject = Field()
    url = Field()
    title = Field()
    crn = Field()
    prereqs = Field()
    
    def __eq__(self,other):
        """
        Two courses are equal if their subject and number are the same
        """
        
        return (self['number'] == other['number'] and 
                self['subject'] == other['subject'])
                
class ScheduleItem(Item):
    subject = Field()
    number = Field()
    term = Field()
    crn = Field()
    capacity = Field()
    enrollment = Field()

class Course(Item):
    """
    Data structure to be exported
    
    Contains a single course with enrollment data from all terms and sections
    """
    number = Field()
    subject = Field()
    calendar_url = Field()
    catalog_url = Field()
    title = Field()
    description = Field()
    terms_offered = Field()
    prereqs = Field()
    
    def __init__(self,other=None):
        Item.__init__(self)
        
    
    def __eq__(self,other):
        """
        Two courses are equal if their subject and number are the same
        """
        
        return (self['number'] == other['number'] and 
                self['subject'] == other['subject'])
        
