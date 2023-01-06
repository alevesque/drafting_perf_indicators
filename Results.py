from ._anvil_designer import ResultsTemplate
from anvil import *
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
from ..Log import Log
log_1 = Log()
import datetime


class Results(ResultsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    #get lists of designers and classification from dropdowns on Log page
    [self.designer_list, self.classification_list] = log_1.get_item_lists()
    self.plot_parameters_config()
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
          if(not y['Time_to_Completion']):
            open_count += 1
          else:
            closed_count += 1
            duration += y['Time_to_Completion']
        #dont divide by zero
        if(closed_count!=0):
          self.duration_per_designer_and_class[j][i] = duration//closed_count
        else:
          self.duration_per_designer_and_class[j][i] = 0
        self.open_requests_per_designer_and_class[j][i] = open_count
        
    pass #requests_per_designer_and_class, duration_per_designer_and_class, open_requests_per_designer_and_class
  
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
    #[self.requests_per_designer_and_class, self.duration_per_designer_and_class, self.open_requests_per_designer_and_class] = self.calculate_results()
    self.calculate_results()
    self.draw_all_plots()
    '''self.days_to_complete_plot.redraw()
    self.req_per_period_plot.redraw()
    self.open_req_plot.redraw()'''
    pass

  def plot_parameters_config(self,**args):
    #sets plot theme arguments
    self.plot_params = {
      'marker': {
        'line': {
          'width': 1,
          'color': 'black'
        }},
      'x': self.designer_list,
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
    datasets = [self.requests_per_designer_and_class,self.duration_per_designer_and_class, self.open_requests_per_designer_and_class]
    plot_names = ['Requests','Turnaround Time','Open Requests']
    nuc = ['New','Update','Correction']
    graphs = [self.req_per_period_plot, self.days_to_complete_plot, self.open_req_plot]
    
    #reset plots between calls so data doesnt stack up
    for prev_data in graphs:
      prev_data.data = []
    
    if(self.two_weeks_radio_button.selected):
      self.title_period = self.two_weeks_radio_button.text
    else:
      self.title_period = self.all_time_radio_button.text 
      
    #adding plotly graphs to plot objects in graph[] plots those datasets with the given options
    for index_data,datas in enumerate(datasets):
      for index_graphs, row in enumerate(datas):
        graphs[index_data].data += [ go.Bar(y=row[:],name=nuc[index_graphs],**self.plot_params)]
      self.plot_layout['title'] = {
        'text': '{0} - {1}'.format(plot_names[index_data],self.title_period)
      }
      graphs[index_data].layout = self.plot_layout    
    pass

  def log_menu_button_copy_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('Results')
    pass






