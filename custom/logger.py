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


class FeedbackLogger():
    def __init__(self):
        self.logger = logging.getLogger('feedback')
        feedbackhandler = logging.FileHandler('feedback.log', mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        feedbackhandler.setFormatter(formatter)
        self.logger.addHandler(feedbackhandler)
        self.logger.setLevel(logging.INFO)