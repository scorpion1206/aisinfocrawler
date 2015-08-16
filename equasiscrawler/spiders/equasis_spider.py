import scrapy
import sys
import csv
from scrapy.shell import inspect_response
from equasiscrawler.items import EquasiscrawlerItem
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

class EquasisSpider(scrapy.Spider):
    name = 'equasisspider'
    allowed_domains = ["equasis.org"]   
    
    user_name = ['multisystem126@yopmail.com', 'multisystem126@gmail.com']
    user_password = ['hieu1206','hieu1206']
    user_index = 0
    
    login_url = 'http://www.equasis.org/EquasisWeb/authen/HomePage?fs=HomePage'
    dwr_url = 'http://www.equasis.org/EquasisWeb/dwr/call/plaincall/__System.generateId.dwr'
    search_url = 'http://www.equasis.org/EquasisWeb/restricted/ShipList?fs=ShipSearch'
    logout_url = 'http://www.equasis.org/EquasisWeb/public/HomePage?fs=HomePage&P_ACTION=NEW_CONNECTION'
    
    session_id = ''
    dwr_session_id = ''
    
    imo_file = ''
    imo_list = []
    
    #db_cols = ['imo','ship_name','call_sign','mmsi','gross_tonnage','dwt','ship_type','year_of_build','flag','ship_status','last_update']
    db_cols = {
         'IMO number':'imo','Name of ship':'ship_name','Call Sign':'call_sign','MMSI': 'mmsi',
         'Gross tonnage':'gross_tonnage','DWT':'dwt','Type of ship':'ship_type',
         'Year of build':'year_of_build','Flag':'flag','Status of ship':'ship_status',
         'Last update':'last_update'}

    def __init__(self, *args, **kwargs):
        super(EquasisSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        input_file=kwargs.get('input')
        print str(input_file)
        try:
            if len(input_file) > 1:
                self.imo_file = open(str(input_file),'r')
            else:
                self.imo_file = open('tmp.json', 'r')            
        except IOError:
            print "Error: can\'t find file or read data"
            return
        else:
            print "Yielding POST request with imo_number"  
            self.imo_list = self.imo_file.readlines()
        
    def spider_closed(self):
        if not self.imo_file.closed:
            self.imo_file.close()
        print 'Crawling finished!'        

    def start_requests(self):
        return [scrapy.FormRequest(self.login_url,formdata={'j_email': self.user_name[self.user_index], 'j_password': self.user_password[self.user_index], 'submit': 'Ok'},
                                   callback=self.check_login)]

    #Check if login succeeds
    def check_login(self, response):
        print response.headers
        if "Logout" in response.body:
            self.log("\n\n Successfully logged in. Retrieve sesison_id and dwr_session_id first.\n\n")
            tmp_header=response.headers
            self.session_id=tmp_header['Set-Cookie'].split(';')[0].split('=')[1]
            frmdata={'callCount': '1', 'c0-scriptName': '__System', 'c0-methodName': 'generateId', 'c0-id': '0', 'batchId': '0', 'instanceId': '0', 'page': '/EquasisWeb/authen/HomePage?fs=HomePage', 'scriptSessionId' : '', 'windowName' : ''  }            
            dwr_request = scrapy.FormRequest(self.dwr_url, formdata=frmdata, callback=self.get_dwr_session_id)
            return dwr_request
        else:
            self.log("\n\n\n Login Failed(\n\n\n")
    
    #DWR is required by the Equasis cookies
    def get_dwr_session_id(self, response):
        self.dwr_session_id=response.body.split('\n')[5].split('(')[1].split(')')[0].split('"')[5]
        print 'session_id=' + str(self.session_id) + ' dwr_session_id=' + str(self.dwr_session_id)
        return self.yield_list_imo()

    #Log out
    def logout(self):
        url="http://www.equasis.org/EquasisWeb/public/HomePage?fs=HomePage&P_ACTION=NEW_CONNECTION"
        frmcookies=[{'name': 'DWRSESSIONID','value': self.dwr_session_id,'domain': 'equasis.org','path': '/EquasisWeb'}, {'name': 'JSESSIONID','value': self.session_id,'domain': 'equasis.org','path': '/EquasisWeb'}]
        return scrapy.Request(url, cookies=frmcookies, callback=self.check_logout)
        
    def check_logout(self, response):
        if "Registration" in response.body:
            self.log("\n\n Successfully logged out.\n\n")       
        else:
            self.log("\n\n\n Logout Failed(\n\n\n")        
      
    #Read imo number form file, create POST request to get data  
    def yield_list_imo(self):
        print "Yielding POST request with imo_number, size = " + str(len(self.imo_list))
        for index,imo_number in enumerate(self.imo_list):                
            #print "imo_number = " + str(imo_number)                
            frmdata={'P_PAGE': '1', 'P_IMO': imo_number.strip(), 'P_CALLSIGN': '', 'P_NAME': '', 'Submit': 'SEARCH' }                
            frmcookies=[{'name': 'DWRSESSIONID','value': self.dwr_session_id}, {'name': 'JSESSIONID','value': self.session_id}]
            ship_info_request = scrapy.FormRequest(self.search_url, formdata=frmdata, cookies=frmcookies,dont_filter=True,callback=self.parse)                                
            #print "REQUEST IS = " + ship_info_request.url + " " + ship_info_request.method + " " + ship_info_request.body + " "
            #print "COOKIES = " +  str(ship_info_request.cookies)
            yield ship_info_request  
    
    #Parse the response to get SHIP information    
    def parse(self,response):        
        #inspect_response(response, self)
        row_list=response.xpath('//table[@class="encart"]/tbody/tr')
        print "row_list_len ===== " + str(len(row_list))  
        item = EquasiscrawlerItem()
        for index, row in enumerate(row_list):
            col_list=row.xpath('.//td')
            if len(col_list) > 1:
                title = col_list[0]
                col = col_list[1]
                title_data=title.xpath('text()').extract()
                col_data=col.xpath('text()').extract()
                if len(col_data) > 0:     
                    tmp_title_idx=title_data[0].split(':')[0].strip().encode('utf-8')
                    if tmp_title_idx in self.db_cols:
                        if ',' in col_data[0]:
                            col_data[0] = col_data[0].replace(',', '-')
                        item[self.db_cols[tmp_title_idx]] = col_data[0]
        yield item