from ._anvil_designer import ResultsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
from ..Log import Log
log_1 = Log()
import datetime
import calendar


class Results(ResultsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    if(Log().user['admin']):
      self.admin_panel_button_results_page.visible = True
      
    #get lists of designers and classification from dropdowns
    a = app_tables.dropdowns.search()
    self.classification_list = [row['class_listing'] for row in a if(row['class_listing'])]
    self.designer_list = [row['designer_listing'] for row in a if(row['designer_listing'])]
    self.mos = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    #[self.designer_list, self.classification_list] = log_1.get_item_lists()
    #self.plot_parameters_config()
    #update graphs
    self.refresh_tables()
    pass
  
  def calculate_results(self, *args):
    '''
    results_raw is a 4-D list with rows of classification and columns of designer.
    
    Each element is a list of data table rows (Type: SearchIterator is a list of dicts, essentially) that 
    match the two attributes Classification and Designer.
    
    in turn,each row is a dict of data table values from the Results Data Table
    '''
    results_raw = [[0]*len(self.designer_list) for count in range(len(self.classification_list))]
    
    #the rest just store 2D lists of values for plotting, calculated from results_raw
    self.requests_per_designer_and_class = [[0]*len(self.designer_list) for count in range(len(self.classification_list))]
    self.duration_per_designer_and_class = [[0]*len(self.designer_list) for count in range(len(self.classification_list))]
    self.open_requests_per_designer_and_class = [[0]*len(self.designer_list) for count in range(len(self.classification_list))]

    # initialize lists used below
    self.monthly_requests_per_class = [[0]*12 for count in range(3)]
    self.monthly_delivered_requests_per_class = [[0]*12 for count in range(3)]
    self.monthly_open_requests_per_class = [[0]*12 for count in range(3)]
    self.requests_dept_total = [[0]*12 for count in range(3)]
    self.duration_dept_total = [[0]*12 for count in range(3)]
    self.open_requests_dept_total = [[0]*12 for count in range(3)]
    
    
    current_date = datetime.date.today()
    for month_index, month in enumerate(self.mos):
      # get first and last days in current month
      day_one = datetime.date(year=current_date.year,month=month_index+1,day=1)
      last_day = calendar.monthrange(current_date.year, month_index+1)[1]
      day_end = datetime.date(year=current_date.year,month=month_index+1,day=last_day)
      
      # if it's december, first day next month is jan 01 next year
      if month_index < 11:
        next_month_day_one = datetime.date(year=current_date.year,month=month_index+2,day=1)
      else:
        # otherwise it's next month day 1
        next_month_day_one = datetime.date(year=current_date.year+1,month=1,day=1)
        
      for class_index, doc_classification in enumerate(self.classification_list):
        # search for all requests for the current classification (new, update, correction) in the current month
        self.monthly_requests_per_class[class_index][month_index] = app_tables.requests.search(Classification=doc_classification,Date_Requested=q.any_of(q.between(day_one,day_end,min_inclusive=True,max_inclusive=True),q.all_of(None)))
        # search for all requests with a delivery date in the current month
        self.monthly_delivered_requests_per_class[class_index][month_index] = app_tables.requests.search(Classification=doc_classification,Date_Delivered=q.any_of(q.between(day_one,day_end,min_inclusive=True,max_inclusive=True),q.all_of(None)))
        #if it's the present month, find open records to date
        if month_index + 1 == current_date.month:
          # open record at this current month is one that has never been closed or was closed in a month after the current month.
          self.monthly_open_requests_per_class[class_index][month_index] = app_tables.requests.search(Classification=doc_classification, Date_Requested=q.less_than_or_equal_to(current_date),Date_Delivered=q.any_of(q.greater_than(current_date),q.all_of(None)))
          # don't care about the contents, just want to plot the raw count per month per classification
          self.open_requests_dept_total[class_index][month_index] = len(self.monthly_open_requests_per_class[class_index][month_index])
        # if it's a prior month, find requests that were open at the time the month ended (request date before end of month, deliv date after or none (ie still open))
        # this matters so that the 12 month open requests graph shows a progression and doesnt erase the history every time it's called and a request was closed
        elif month_index + 1 < current_date.month:
          self.open_requests_dept_total[class_index][month_index] = len(app_tables.requests.search(Classification=doc_classification,Date_Requested=q.any_of(q.less_than_or_equal_to(day_end),q.all_of(None)),Date_Delivered=q.any_of(q.all_of(None),q.greater_than_or_equal_to(next_month_day_one))))
        #if it's a future month, nothing has happened yet
        else:
          self.open_requests_dept_total[class_index][month_index] = 0
        self.requests_dept_total[class_index][month_index] = len(self.monthly_requests_per_class[class_index][month_index])
        
        # count open requests
        open_count_total = 0
        closed_count_total = 0
        duration_total = 0
        for request in self.monthly_delivered_requests_per_class[class_index][month_index]:
          if(request['Time_to_Completion'] == None):
            open_count_total += 1
          else:
            closed_count_total += 1
            duration_total += request['Time_to_Completion']
        #dont divide by zero
        if(closed_count_total != 0):
          self.duration_dept_total[class_index][month_index] = duration_total/closed_count_total
        else:
          self.duration_dept_total[class_index][month_index] = 0      
               
    #set time period to graph over
    if self.two_weeks_radio_button.selected == True:
      #if delivery date is in past two weeks
      current_date = datetime.date.today()
      date_period = current_date - datetime.timedelta(days=14)
      pass
    else:
      #if plotting for all time, use unix epoch for start date
      date_period = datetime.date(year=1970,month=1,day=1)
      pass
    #now cycle through the Data Table to get values for each Classification/Designer pair
    #probably makes it slow but this shouldnt be getting called a lot, just when you refresh the page or date range
    for i, person in enumerate(self.designer_list):
      for j, doc_classification in enumerate(self.classification_list):
        #some searches return multiple matches, and some return nothing
        #therefore, 3rd dimension of results_raw has varying lengths
        results_raw[j][i] = app_tables.requests.search(Classification=doc_classification,Designer=person,Date_Delivered=q.any_of(q.greater_than(date_period),q.all_of(None)))
        
        #to get number of requests, simply get length of that Classification/Designer pair
        self.requests_per_designer_and_class[j][i] = len(results_raw[j][i])
        
        #count results for this Classification/Designer pair that don't have completion times (ie are open)
        #otherwise, they have completion times so find the average average duration of requests
        open_count = 0
        closed_count = 0
        duration = 0
        for y in results_raw[j][i]:
          if(y['Time_to_Completion'] == None):
            open_count += 1
          else:
            closed_count += 1
            duration += y['Time_to_Completion']
        #dont divide by zero
        if(closed_count!=0):
          self.duration_per_designer_and_class[j][i] = duration/closed_count
        else:
          self.duration_per_designer_and_class[j][i] = 0
        self.open_requests_per_designer_and_class[j][i] = open_count
        
    pass
  
  def logout_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.users.logout()
    pass

  def log_menu_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('Log')
    pass

  def all_time_radio_button_clicked(self, **event_args):
    """This method is called when this radio button is selected"""
    #if clicked refresh graphs
    self.refresh_tables()
    pass

  def two_weeks_radio_button_clicked(self, **event_args):
    """This method is called when this radio button is selected"""
    #if clicked refresh graphs
    self.refresh_tables()
    pass
  
  def refresh_tables(self,**args):
    #TODO: may not actually redraw graphs - add data pre-two weeks and check
    #recalculate graphs
    self.calculate_results()
    self.draw_all_plots()
    '''self.days_to_complete_plot.redraw()
    self.req_per_period_plot.redraw()
    self.open_req_plot.redraw()
    self.req_yearly_dept_total_plot.redraw()'''
    pass

  def plot_parameters_config(self,opt='',**args):
    if 't' in opt:
      x_label = self.mos
    else:
      x_label = self.designer_list
    #sets plot theme arguments
    self.plot_params = {
      'marker': {
        'line': {
          'width': 1,
          'color': 'black'
        }},
      'x': x_label,#self.designer_list,
      'barmode': 'group',
      'bargap': 0.15,
      'bargroupgap': 0.1
    }
    self.plot_layout = {
      'showlegend': 'True',
      'marker_line': {
        'width':'10',
        'color':'black'
      }
    }
    pass

  def draw_all_plots(self,**args):
    # data and plot titles to iterate over
    datasets = [self.requests_per_designer_and_class, self.duration_per_designer_and_class, self.open_requests_per_designer_and_class]
    total_datasets = [self.requests_dept_total, self.duration_dept_total, self.open_requests_dept_total]
    plot_names = ['Requests','Turnaround Time','Open Requests']
    total_plot_names = ['Requests - Dept Total', 'Turnaround Time - Dept Total', 'Open Requests - Dept Total']
    graphs = [self.req_per_period_plot, self.days_to_complete_plot, self.open_req_plot]
    total_graphs = [self.req_yearly_dept_total_plot, self.duration_total_plot, self.open_requests_total_plot]
    
    #reset plots between calls so data doesnt stack up
    for prev_data in graphs:
      prev_data.data = []
    for prev_data_total in total_graphs:
      prev_data_total.data = []
    
    if(self.two_weeks_radio_button.selected):
      self.title_period = self.two_weeks_radio_button.text
    else:
      self.title_period = self.all_time_radio_button.text 
      
    # adding plotly graphs to plot objects in graph[] plots those datasets with the given options
    self.plot_parameters_config()
    # plot indicators per designer
    for index_data, datas in enumerate(datasets):
      for index_graphs, row in enumerate(datas):     
        graphs[index_data].data += [ go.Bar(y=row[:],name=self.classification_list[index_graphs],**self.plot_params)]
      self.plot_layout['title'] = {
        'text': '{0} - {1}'.format(plot_names[index_data],self.title_period)
      }
      graphs[index_data].layout = self.plot_layout
      
    # changes xlabel to months rather than designers
    self.plot_parameters_config(opt='t')
    # plot 12 month graphs for dept totals
    for total_index_data, total_datas in enumerate(total_datasets):
      for total_index_graphs, total_row in enumerate(total_datas):
        total_graphs[total_index_data].data += [ go.Bar(y=total_row[:],name=self.classification_list[total_index_graphs],**self.plot_params)]
      self.plot_layout['title'] = {
        'text': '{0}'.format(total_plot_names[total_index_data])
      }
      total_graphs[total_index_data].layout = self.plot_layout
    pass

  def log_menu_button_copy_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('Results')
    pass

  def admin_panel_button_results_page_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('Admin_Panel')
    pass
