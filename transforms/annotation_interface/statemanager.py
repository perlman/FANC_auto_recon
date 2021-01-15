class StateManager: 
    
    ''' Class for keeping track of JSON states.'''
    def __init__(self,
                 filename=None,
                 token=None):
        
        self.directory = Path.home() / 'cloudvolume'
        if filename is None:
            self.filename = self.directory / 'json_states.csv'
        
        self.__initialize()
        
        
    def __initialize(self):
        # Check if the database exists, if not create a new one.
        fileEmpty =  os.path.exists(self.filename)
        if not fileEmpty:
            df = pd.DataFrame(columns=['state_id','description'])
            df.to_csv(self.filename,index=False)
        self.get_database()
        print(self.df) 
    
    def get_database(self):
        # Read database. 
        self.df  = pd.read_csv(self.filename)
        
 
    def add_state(self, state_id, description=None):
        
        filename = self.filename
        df = pd.DataFrame([{'state_id':state_id,'description':description}])
        df.to_csv(filename, mode='a', header=False,index=False, encoding = 'utf-8')
        df.get_database()
        return('state added')
 
    def get_state(self,state_id):
        return(client.state.get_state_json(state_id))
    
    def get_url(self,state):
        return('https://neuromancer-seung-import.appspot.com/?json_url=https://api.zetta.ai/json/' + str(state))
        