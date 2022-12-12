import logging
import pandas as pd
from Logging.Customlogger import class_customlogger
from Scrapping_operations.webscrapper import scrapper
from db_connection.Databaseoperations import Mongodb_operations
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from bson.json_util import dumps

app = Flask(__name__)


@app.route('/', methods=['GET','POST'])  # route to display the home page
@cross_origin()
def homePage():
    db_operation = Mongodb_operations(db_name="ineuron_courses")
    db_operation.get_or_create_collection("Coursedata_Summary")

    if request.method == 'POST':
        filtered_data=[]
        condition = request.json['query']
        for i in db_operation.filter_data_from_db(condition):
            filtered_data.append(i)

        return dumps(filtered_data)

    else:
        li = []
        for i in db_operation.get_all_data_from_db():
            li.append(i)

        return dumps(li)

class main_page(scrapper):
    def __init__(self):
        self.log_main = class_customlogger.custom_logger_fn(logger_name=__name__, logLevel=logging.DEBUG,
                                                            log_filename="main.log")
        self.log_main.info("Initialising the home settings")
        self.db_operation = Mongodb_operations(db_name="ineuron_courses")
        self.db_operation.get_or_create_collection("Coursedata_Summary")
        sc_obj = scrapper(self.db_operation)
        # links_df = sc_obj.get_course_categories_and_links()
        # course_data_main = sc_obj.parse_course_links(links_df["Course_URL"])
        # links_df=["https://ineuron.ai/course/Java-Full-Stack-Developer-Course"]
        # course_data_main = sc_obj.parse_course_links(links_df)


if __name__ == "__main__":
    # mp = main_page()
    # data = mp.db_operation
    app.run(host='127.0.0.1', port=5000, debug=True)
