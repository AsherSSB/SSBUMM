import logging

class PlayerReportLogger():
    def __init__(self):
        self.logger = logging.getLogger('player_report')
        playerrephandler = logging.FileHandler('playerreport.log', mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        playerrephandler.setFormatter(formatter)
        self.logger.addHandler(playerrephandler)
        self.logger.setLevel(logging.INFO)

class BugReportLogger():
    def __init__(self):
        self.logger = logging.getLogger('bug_report')
        bugreporthandler = logging.FileHandler('bugreports.log', mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        bugreporthandler.setFormatter(formatter)
        self.logger.addHandler(bugreporthandler)
        self.logger.setLevel(logging.INFO)