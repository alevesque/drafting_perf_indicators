from ._anvil_designer import LogTemplate
from anvil import *
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import re
import datetime




class Log(LogTemplate):
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    # Any code you write here will run before the form opens.
    self.log_panel.items = app_tables.requests.search()
    self.sort_order_reverse = False
    
  def results_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('Results')
    pass

  def logout_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.users.logout()
    pass

  def add_edit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('Log')
    pass
  
  #for using lists of values in Return form
  def get_item_lists(self, **args):
    designer_list = self.designer_dropdown.items
    classification_list = self.classification_dropdown.items
    return designer_list, classification_list
  
  #refreshes the table view pane
  def refresh_table(self,*args):
    self.log_panel.items = app_tables.requests.search(*args)
    return
  
  def reset_interface(self,**args):
    #reset UI to search mode
    self.search_button.text = 'Search'
    self.search_button.background = ''
    self.add_button.text = 'Add Record'
    self.add_button.background = ''
    #reset user fields
    self.type_dropdown.selected_value = None
    self.classification_dropdown.selected_value = None
    self.designer_dropdown.selected_value = None
    self.pn_text_box.text = None
    self.req_date_picker.date = None
    self.deliv_date_picker.date = None
  
  #checks if user entered a valid P/N and returns dict with record info
  def validate_user_request(self,**args):
    pattern = re.compile("^([0-9]{4}\-[0-9]{5}\-M?[A|B])$")
    if(pattern.match(self.pn_text_box.text)):
      new_request = {
        'Type':self.type_dropdown.selected_value,
        'Classification':self.classification_dropdown.selected_value,
        'Designer':self.designer_dropdown.selected_value,
        'PN_Affected':self.pn_text_box.text,
        'Date_Requested':self.req_date_picker.date,
        'Date_Delivered':self.deliv_date_picker.date
      }
    else:
      if(self.pn_text_box.text):
        self.error_label.text = 'Regex Error - Check P/N. Currently only search by part number is implemented.'
      new_request=None
      return new_request
    
    #check if user added a delivery date and calculate time to completion
    if(self.deliv_date_picker.date and self.req_date_picker.date):  
      if self.req_date_picker.date > self.deliv_date_picker.date:
        self.error_label.text = 'Request date cannot be after delivery date.'
        return
      else:
        new_request['Time_to_Completion']=(self.deliv_date_picker.date-self.req_date_picker.date).days
    '''if(not self.req_date_picker.date):
      self.error_label.text = 'Record requires request date.'
      return'''
    #elif(not self.type_dropdown.selected_value)
    
    return new_request
    
  def add_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if(self.add_button.text == 'Add Record'):
      self.error_label.text = ''

      #check if whatever was in the fields exists and was formatted properly
      new_request = self.validate_user_request()
      if(new_request):
        if(not new_request['Date_Requested']):
          self.error_label.text = 'Please add a request date.'
          return
        
        #check if there is already an open request for this p/n
        duplicate_rows = app_tables.requests.search(PN_Affected=new_request['PN_Affected'])
        if(duplicate_rows):
          #if request does not have a completion date (i.e., it hasn't been closed), stop record creation
          for row in duplicate_rows:
            if(not row['Time_to_Completion']):
              self.error_label.text = 'Duplicate record. Close out existing requests for this P/N before creating a new one.'
              return
          
        #check if user added a delivery date and calculate time to completion
        '''if(self.deliv_date_picker.date):
          new_request['Time_to_Completion']=(self.deliv_date_picker.date-self.req_date_picker.date).days'''
        
        #create new record and update the view
        app_tables.requests.add_row(**new_request)
        self.error_label.text = 'Submitted!'
        self.refresh_table()    
        
    elif(self.add_button.text == 'Cancel'):
      #if in edit mode, button cancels the edit and switches UI back to search mode when clicked
      self.refresh_table()
      self.reset_interface()
    

  def search_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    '''click search
    if one match, bring up in boxes
    if multiple, give error and show possible matches in log panel items
    search button becomes green confirm edit button
      saves row and gives success message
    add button becomes red cancel button
      clears boxes text, exits function and gives cancel message
    '''
    #when in search mode
    if(self.search_button.text=='Search'):
      self.error_label.text = ''
      #get data from fields
      user_request_raw = self.validate_user_request()
      user_request = dict()
      #if theres data, search for record
      if(user_request_raw):        
        for field in user_request_raw:
          #dont search for fields the user didnt fill out
          if user_request_raw[field]!=None and field!='Time_to_Completion':
            user_request[field] = user_request_raw[field]
          #except for delivery date so user can find open requests
          #note: nvm , doing this make it so you cant see closed records
          #just have user close record to make it unique when they want to edit
          #elif field == 'Date_Delivered':
            #user_request['Date_Delivered'] = None
  
        print(user_request)
        #look for record(s) with values matching user input
        record_to_edit = app_tables.requests.search(**user_request)
        self.log_panel.items = record_to_edit
        #check how many results matched
        if(len(record_to_edit)>1):
          #if more than one match, show possible matches in table view pane and return error msg
          self.error_label.text = 'Multiple matching records found, see below and refine search.'
          
        elif(len(record_to_edit)==0):
          self.error_label.text = 'No records found.'
        elif(len(record_to_edit)==1):
          #get dict from list of dicts
          record_to_edit = record_to_edit[0]
          #store unique row id value for saving the record later
          self.row_id = record_to_edit.get_id()

          #pull up values from record
          if(record_to_edit['Type']):
            self.type_dropdown.selected_value = record_to_edit['Type']
          if(record_to_edit['Classification']):
            self.classification_dropdown.selected_value = record_to_edit['Classification']
          if(record_to_edit['Designer']):
            self.designer_dropdown.selected_value = record_to_edit['Designer']
          if(record_to_edit['PN_Affected']):
            self.pn_text_box.text = record_to_edit['PN_Affected']
          if(record_to_edit['Date_Requested']):
            self.req_date_picker.date = record_to_edit['Date_Requested']
          if(record_to_edit['Date_Delivered']):
            self.deliv_date_picker.date = record_to_edit['Date_Delivered']
            
          #TODO: boxes change color to indicate it's been pulled up?
          
          #search was pulled up so we are now in search mode
          #buttons change color and text. text values change functionality in the event trigger methods
          self.search_button.text = 'Confirm Edit'
          self.search_button.background = '#78d049'
          self.add_button.text = 'Cancel'
          self.add_button.background = '#c44a4a'
        pass
      else:
        #if no user request, search button just refreshes the table view (only way to get out of the multiple results view for now)
        self.refresh_table()
    elif(self.search_button.text=='Confirm Edit'):
      #in record edit mode
      edited_record_data = self.validate_user_request()
      
      #the unique row id value we got earlier allows us to pull up the row from the data table
      record_to_edit = app_tables.requests.get_by_id(self.row_id)
      
      #reset cheat attribute for next time
      self.row_id = ''
      
      #update record with new user edited values
      record_to_edit.update(**edited_record_data)
      self.error_label.text = 'Edit submitted!'
      
      #reset interface to search mode
      self.reset_interface()
      self.refresh_table()
    pass
  
  def sort_data_grid(self, *args):
    user_sort_field = args[0] #dict key in Data Table to sort by; 'Designer' etc
    user_sort_button = args[1] #name of link object
    
    
    #reset other icons to default when new sort is employed
    links_list = [self.pn_sort_link,self.type_sort_link,self.classification_sort_link,self.designer_sort_link,self.date_req_sort_link,self.date_deliv_sort_link,self.completion_time_sort_link]
    for link in links_list:
      if link != (user_sort_button) and link.icon != 'fa:sort-alpha-asc':
        link.icon = 'fa:sort-alpha-asc'
    
    #when icon is clicked, flip sort direction and change icon to match
    self.sort_order_reverse = not self.sort_order_reverse 
    if self.sort_order_reverse == True:
      user_sort_button.icon = 'fa:sort-alpha-desc'
    else:
      user_sort_button.icon = 'fa:sort-alpha-asc'
    
    #sort data by user selected field and order, then update table
    #use anvil sort method because their python to javascript implementation of sorted() doesnt work with dicts
    self.refresh_table(tables.order_by(user_sort_field, ascending=(not self.sort_order_reverse)))
    pass
  
  '''
  ############################################
  On click methods for icons in column headers
  ############################################
  These methods send their respective Data Table key to sort by, as well as the object that was clicked
  so that the icons etc can be updated.
  '''
  def pn_sort_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    sort_field = 'PN_Affected'
    self.sort_data_grid(sort_field,self.pn_sort_link)
    pass

  def type_sort_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    sort_field = 'Type'
    self.sort_data_grid(sort_field,self.type_sort_link)
    pass

  def classification_sort_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    sort_field = 'Classification'
    self.sort_data_grid(sort_field,self.classification_sort_link)
    pass

  def designer_sort_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    sort_field = 'Designer'
    self.sort_data_grid(sort_field,self.designer_sort_link)
    pass

  def date_req_sort_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    sort_field = 'Date_Requested'
    self.sort_data_grid(sort_field,self.date_req_sort_link)
    pass

  def date_deliv_sort_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    sort_field = 'Date_Delivered'
    self.sort_data_grid(sort_field,self.date_deliv_sort_link)
    pass

  def completion_time_sort_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    sort_field = 'Time_to_Completion'
    self.sort_data_grid(sort_field,self.completion_time_sort_link)
    pass








  
  
  
  

  
  
 









