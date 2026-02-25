import time

class CsvExporter:
    def __init__(self, key_id):
        self.key_id = key_id
        self.start_time = time.time()
        
    def export(self, granularity="hour"):
        # Not needed for logic, but might be helpful if we want a helper
        pass
