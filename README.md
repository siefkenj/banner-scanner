banner-scanner
==============

Scrape class data, prerequisites, previous dates offered, etc. from BANNER university content management systems.


Usage
=============
In the root directory of the project, type:
	scrapy crawl banner

By default, the scraper will grab all the classes in the course catalog, to restrict the search
to certain subjects, open the file 'banner_spider.py', and edit the variables 'TEST_SUBJECTS', and
'TEST_RUN' at the top of the file.
