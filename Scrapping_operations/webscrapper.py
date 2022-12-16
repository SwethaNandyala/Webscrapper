import logging
import os.path
from openpyxl import Workbook
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup as bs
from Logging.Customlogger import class_customlogger
from db_connection.Databaseoperations import Mongodb_operations


class scrapper:

    def __init__(self, db_operation_obj: Mongodb_operations):
        self.log = class_customlogger.custom_logger_fn(logger_name=__name__, logLevel=logging.DEBUG,
                                                       log_filename="scrapper.log")
        self.url = "https://ineuron.ai/courses"
        self.course_data_main = []
        self.course_links_main = []
        self.path = './chromedriver.exe'
        self.driver = webdriver.Chrome(executable_path=self.path, options=self.set_chrome_options())
        self.db_operation_obj = db_operation_obj
        self.course_summary = {
            "Course_Category": "",
            "Course_Subcategory": "",
            "Course_Title": "",
            "Course_Description": "",
            "Course_Instructor_Details": [],
            "Course_Fee": "",
            "Course_Requirements": [],
            "Course_Features": [],
            "Course_Learnings": [],
            "Course_Curriculum": []
        }

    def scroll_down(self):
        try:
            self.log.info("scrolling down")
            SCROLL_PAUSE_TIME = 0.5
            # Get scroll height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                # Scroll down to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                # Wait to load page
                time.sleep(SCROLL_PAUSE_TIME)
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    #no more data is present to scroll down
                    break
                last_height = new_height
            self.log.info("scrolled down")
        except Exception as e:
            self.log.exception(e)

    def scroll_up(self):

        try:
            self.log.info("scrolling up")
            self.driver.execute_script("window.scrollTo(0,0)")
            self.log.info("scrolled_up")
        except Exception as e:
            self.log.exception(e)

    def fetch_course_links(self):
        course_main_html = bs(self.driver.page_source, "html.parser")
        list_main_pg_right_boxes = course_main_html.findAll("div", {"class": "Course_right-area__JqFFV"})
        list_course_links = [i.a["href"] for i in list_main_pg_right_boxes]
        list_course_links = list(set(list_course_links))
        home = self.url.replace("courses", "")
        list_course_links = [home + i for i in list_course_links]
        return list_course_links

    def tick_categories(self):
        try:
            self.log.info("Getting the course links")
            checkboxes_label = '//*[@id="' + '__next"]/div[1]/section[3]/div/div/div[1]/div[2]/div[1]/div[2]/div/label'
            num_checkboxes = len(self.driver.find_elements_by_xpath(checkboxes_label))
            list_categories = [i.text for i in self.driver.find_elements_by_xpath(checkboxes_label)]
            for box in range(num_checkboxes):
                # for box in range(2):
                self.log.info(f"selecting the category {list_categories[box]} ")
                self.driver.find_elements_by_xpath(checkboxes_label)[box].click()
                self.scroll_down()
                time.sleep(4)
                self.scroll_up()
                self.course_links_main.append(
                    pd.DataFrame({"category": list_categories[box], "Course_URL": self.fetch_course_links()},
                                 index=None))
                # uncheck the category
                self.driver.find_elements_by_xpath(checkboxes_label)[box].click()
            return self.course_links_main
        except Exception as e:
            self.log.exception(e)

    def get_course_categories_and_links(self):
        self.open_url()
        try:
            links_list = self.tick_categories()
            self.log.info("List of course links received")
            links_df = pd.DataFrame()
            for each_df in links_list:
                links_df = pd.concat([links_df, each_df], ignore_index=True)

            if not os.path.exists("Output"):
                self.log.info("The output folder doesnt exists")
                self.log.info("Creating the output folder")
                os.mkdir("output")
            else:
                self.log.info("The output folder exists")

            self.log.info("saving the links to an excel")
            links_df.to_excel('.\output\Course_links.xlsx', sheet_name="Course_links", index=None)
            return links_df
        except Exception as e:
            self.log.exception(e)

    def open_urlopen_url(self):
        try:
            self.log.info("opening the url")
            self.driver.get(self.url)
            self.driver.maximize_window()
            time.sleep(5)
            # see more option
            see_more_option = '//*[@id="' + '__next"]/div[1]/section[3]/div/div/div[1]/div[2]/div[1]/div[2]/div/span/i'
            self.driver.find_element_by_xpath(see_more_option).click()
            self.log.info("See more Option clicked")

        except Exception as e:
            self.log.exception(e)

    def get_final_set_links(self, list_course_links):
        links_present_in_db = []

        for i in self.db_operation_obj.collection.find({}, {'_id': 1}):
            links_present_in_db.extend(list(i.values()))

        common_links = set(list_course_links).intersection(set(links_present_in_db))

        if(len(common_links)>0):
            self.log.info(f"{len(common_links)}:links are already present in db")
            self.log.info(f"These links are already present in db {common_links}")
            links_not_present_in_db = list(set(list_course_links) - set(links_present_in_db)) + list(set(links_present_in_db) - set(list_course_links))
            self.log.info(f"{len(links_not_present_in_db)}links are not present in db")
            self.log.info(f"These links are not present in db {links_not_present_in_db}")
        else:
            links_not_present_in_db=list_course_links
            self.log.info(f"{len(links_not_present_in_db)}: links are not present in db")
            self.log.info(f"These links are not present in db {links_not_present_in_db}")
        return links_not_present_in_db

    def parse_course_links(self, list_course_links):

        links_not_present_in_db = self.get_final_set_links(list_course_links)

        if len(links_not_present_in_db) > 0:
            self.log.info("Parsing the course data")
            for i in range(len(links_not_present_in_db)):
                # append the present url to the course links
                self.log.info(f" Opening {links_not_present_in_db[i]}")
                self.driver.get(links_not_present_in_db[i])
                self.driver.maximize_window()
                time.sleep(4)
                # close the pop-up by clicking on the cross button
                # self.driver.find_element_by_xpath('//*[@id="' + 'Modal_enquiry-modal__yC3YI"]/div/div[1]/i').click()
                # self.driver.find_element_by_xpath('// *[ @ id = "Modal_enquiry-modal__yC3YI"] / div / div[1] / i').click()

                # click on view more button in the course curriculum
                try:
                    # if view more exists click else pass
                    self.driver.find_element_by_class_name('CurriculumAndProjects_view-more-btn__iZ72A').click()
                except:
                    pass
                # After checking the view button and clicking it execute the final block
                finally:
                    details_of_page_bs = bs(self.driver.page_source, "html.parser")
                    # Course headings and description
                    try:
                        self.course_summary["_id"] = links_not_present_in_db[i]
                        header = details_of_page_bs.find_all("div", {"class": "Hero_left__GNJBa"})
                        category_subcategory = [i.text for i in header[0].find_all('span')]
                        title = header[0].find('h3').text
                        description = header[0].find("div",{"class" : "Hero_course-desc__lcACM"}).text
                        self.course_summary["Course_Category"] = category_subcategory[0]
                        self.course_summary["Course_Subcategory"] = category_subcategory[1]
                        self.course_summary["Course_Title"] = title
                        self.course_summary["Course_Description"] = description
                    except Exception as e:
                        self.log.error(e)

                    # Price details
                    try:
                        # Price details part of a package
                        Price_details = details_of_page_bs.find_all("div", {"class": "CoursePrice_no-cost-emi__Ve__2 text-center"})
                        self.course_summary["Course_Fee"] = Price_details[0].text
                    except:
                        # Price details mentioned directly
                        Price_details = details_of_page_bs.find_all("div", {"class": "CoursePrice_dis-price__Rz6Iz"})
                        self.course_summary["Course_Fee"] = Price_details[0].text

                    # Learnings
                    try:
                        learnings = details_of_page_bs.find_all("div", {"class": "CourseLearning_card__0SWov card"})
                        learning_topics_list = [i.text for i in learnings[0].findAll("li")]
                        self.course_summary["Course_Learnings"] = learning_topics_list
                    except Exception as e:
                        self.log.error(e)

                    # Requirements
                    try:
                        requirements = details_of_page_bs.find_all("div", {"class": "CourseRequirement_card__lKmHf requirements card"})
                        requirements_list = [i.text for i in requirements[0].findAll("li")]
                        self.course_summary["Course_Requirements"] = requirements_list
                    except Exception as e:
                        self.log.error(e)


                    #Course Curriculum

                    #Course curriculum present in CARD: "CurriculumAndProjects_course-curriculum__C9K5U CurriculumAndProjects_card__rF6YN card"
                    #it has various divisions and each div have a topic and list of subtopics divs card " CurriculumAndProjects_curriculum-accordion__fI8wj CurriculumAndProjects_card__rF6YN card"
                    #Topics: CARD: "CurriculumAndProjects_accordion-header__ux_yj CurriculumAndProjects_flex__KmWUD flex"
                    #Subtopics list : CARD "CurriculumAndProjects_accordion-body__qQaIR"

                    try:
                        curriculum = details_of_page_bs.find_all("div", {"class": "CurriculumAndProjects_course-curriculum__C9K5U CurriculumAndProjects_card__rF6YN card"})
                        curriculum_main_list = []
                        for each_div in curriculum[0].find_all("div", {"class": "CurriculumAndProjects_curriculum-accordion__fI8wj CurriculumAndProjects_card__rF6YN card"}):
                            topics = each_div.find("div", {"class","CurriculumAndProjects_accordion-header__ux_yj CurriculumAndProjects_flex__KmWUD flex"})
                            subtopic = each_div.find("div", {"class", "CurriculumAndProjects_accordion-body__qQaIR"})
                            subheadings = [sub.text for sub in subtopic.find_all("li")]
                            curriculum_main_list.append({topics.text: subheadings})
                        self.course_summary["Course_Curriculum"]=curriculum_main_list
                    except Exception as e:
                        self.log.error(e)


                    #Instructor Details

                    try:

                        Instructor_details = details_of_page_bs.find_all("div", {"class": "InstructorDetails_mentor__P07Cj InstructorDetails_card__mwVrB InstructorDetails_flex__g8BFa card flex"})
                        Instructors_list=[]
                        for each_div in Instructor_details:
                            Instructor_details_left = each_div.find("div", {"class": "InstructorDetails_left__nVSdv"})
                            Instructor_name = Instructor_details_left.find("h5").text
                            Instructor_experience = Instructor_details_left.find("p").text
                            Instructor_Social_links = each_div.find("div", {"class": "InstructorDetails_social-links__kuwma InstructorDetails_flex__g8BFa flex"})
                            links = [i["href"] for i in Instructor_Social_links.find_all("a")]
                            Instructors_list.append({"Name":Instructor_name,
                                                     "Description":Instructor_experience,
                                                    "Social Links":links})

                        self.course_summary["Course_Instructor_Details"] = Instructors_list
                    except Exception as e:
                        self.log.error(e)

                    #Course Features
                        try:
                            features = details_of_page_bs.find_all("div", {"class": "CoursePrice_course-features__IBpSY"})
                            features_list = [li_tag.text for li_tag in features[0].find_all('li')]
                            self.course_summary['Course_Features'] = features_list
                        except Exception as e:
                            self.log.error(e)

                self.course_data_main.append(self.course_summary)
                self.log.info("executed the course data method")
                self.db_operation_obj.insert_data(self.course_data_main[i])
            return self.course_data_main
        else:
            self.log.info("All the links are present in db")

    def set_chrome_options(self):
        try:
            self.log.info("Setting the chrome options")
            # create an object of chrome class
            chrome_options = Options()
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("excludeSwitches", ["--disable - popup - blocking"])
            chrome_options.set_capability("pageLoadStrategy", "eager")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-gpu")
            # path of chrome driver
            # Creates a new instance of the chrome driver.
            # Starts the service and then creates new instance of chrome driver.
            # Controls the ChromeDriver and allows you to drive the browser.
            return chrome_options
        except Exception as e:
            self.log.exception(e)
