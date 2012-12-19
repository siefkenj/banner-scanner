# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class BannerItem(Item):
    """
    Data structure received from scraper
    
    Contains a single section of a particular class in a specific term
    """
    number = Field()
    department = Field()
    url = Field()
    title = Field()
    desc = Field()
    term = Field()
    crn = Field()
    prereqs = Field()
    enrollment = Field()    
    
    def __eq__(self,other):
        """
        Two courses are equal if their department and number are the same
        """
        
        return (self['number'] == other['number'] and 
                self['department'] == other['department'])

class Course(Item):
    """
    Data structure to be exported
    
    Contains a single course with enrollment data from all terms and sections
    """
    number = Field()
    department = Field()
    url = Field()
    title = Field()
    desc = Field()
    sections = Field()
    prereqs = Field()
    
    def __eq__(self,other):
        """
        Two courses are equal if their department and number are the same
        """
        
        return (self['number'] == other['number'] and 
                self['department'] == other['department'])
