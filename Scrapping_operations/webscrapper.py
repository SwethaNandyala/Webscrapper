import logging
import os.path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup as bs
from Logging.Customlogger import class_customlogger


class scrapper:

    def __init__(self):
        self.log = class_customlogger.custom_logger_fn(logLevel=logging.DEBUG, fname="scrapper.log")
        self.url = "https://ineuron.ai/"
        self.course_data_main = []
        self.course_links_main = []
        self.set_chrome_options()

    def scroll_down(self, driver):
        try:
            self.log.info("scrolling down")
            SCROLL_PAUSE_TIME = 0.5
            # Get scroll height
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                # Scroll down to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                # Wait to load page
                time.sleep(SCROLL_PAUSE_TIME)
                # Calculate new scroll height and compare with last scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            self.log.info("scrolled down")
        except Exception as e:
            self.log.exception(e)

    def scroll_up(self, driver):

        try:
            self.log.info("scrolling up")
            driver.execute_script("window.scrollTo(0,0)")
            self.log.info("scrolled_up")
        except Exception as e:
            self.log.exception(e)

    def parse_course_links(self, list_course_links, driver, present_url):

        self.log.info("Parsing the course data")
        for i in range(len(list_course_links)):
            # append the present url to the course links
            self.log.info(f" Opening {present_url + list_course_links[i]}")
            driver.get(present_url + list_course_links[i])
            time.sleep(4)
            # close the pop-up by clicking on the cross button
            driver.find_element_by_xpath('//*[@id="' + 'Modal_enquiry-modal__yC3YI"]/div/div[1]/i').click()
            # click on view more button in the course curriculum
            try:
                # if view more exists click else pass
                driver.find_element_by_class_name('CurriculumAndProjects_view-more-btn__iZ72A').click()
            except:
                pass
            else:
                pass
            # After checking the view button and clicking it execute the final block
            finally:
                course_summary = {
                    "course_id": "",
                    "Category": "",
                    "Subcategory": "",
                    "Title": "",
                    "Description": "",
                    "Instructor_Name": [],
                    "Instructor_Details": [],
                    "Fee": "",
                    "Requirements": [],
                    "Course_Features": [],
                    "Course_Curriculum": []
                }

                # category and subcategory
                cat_and_subcat = (
                    driver.find_element_by_class_name("Hero_course-category-breadcrumb__9wzAH")).text.split(">")
                course_summary["Category"] = cat_and_subcat[0]
                course_summary["Subcategory"] = cat_and_subcat[1]
                course_summary["Title"] = driver.find_element_by_class_name("Hero_course-title__4JX81").text
                course_summary["Description"] = driver.find_element_by_class_name("Hero_course-desc__lcACM").text
                # there could be multiple instructors for a course so adding them to a list
                course_summary["Instructor_Name"] = [i.text.split("\n")[0] for i in
                                                     driver.find_elements_by_class_name(
                                                         "InstructorDetails_left__nVSdv")]
                course_summary["Instructor_Details"] = [i.text.split("\n")[1] for i in
                                                        driver.find_elements_by_class_name(
                                                            "InstructorDetails_left__nVSdv")]

                try:
                    course_summary["Fee"] = driver.find_elements_by_xpath("CoursePrice_price__YLG0U")[0].text.split(
                        "\n")
                except:
                    pass
                else:
                    course_summary["Fee"] = driver.find_element_by_xpath(
                        '//*[@id="__next"]/section[3]/div/div/div[2]/div[1]/div[1]').text

                course_summary["Requirements"] = driver.find_element_by_xpath(
                    '//*[@id="__next"]/section[3]/div/div/div[1]/div[2]').text.split("\n")[1:]
                course_summary["Course_Features"] = driver.find_element_by_class_name(
                    'CoursePrice_course-features__IBpSY').text.split("\n")[1:]
                Course_Curriculum = driver.find_element_by_xpath(
                    '//*[@id="__next"]/section[3]/div/div/div[1]/div[3]').text.split("\n")[1:]
                course_summary["Course_Curriculum"] = [course for course in Course_Curriculum if
                                                       course not in (['View More', 'View Less'])]
            self.main_dict.append(pd.DataFrame(course_summary),index=None)
            self.log.info("executed the course data method")


    def fetch_course_links(self, driver):
        course_main_html = bs(driver.page_source, "html.parser")
        list_main_pg_right_boxes = course_main_html.findAll("div", {"class": "Course_right-area__JqFFV"})
        list_course_links = [i.a["href"] for i in list_main_pg_right_boxes]
        list_course_links = list(set(list_course_links))
        list_course_links = [self.url+i for i in list_course_links]
        return list_course_links


    def tick_categories(self, driver):
        try:
            self.log.info("Getting the course links")
            checkboxes_label = '//*[@id="' + '__next"]/div[1]/section[3]/div/div/div[1]/div[2]/div[1]/div[2]/div/label'
            num_checkboxes = len(driver.find_elements_by_xpath(checkboxes_label))
            list_categories = [i.text for i in driver.find_elements_by_xpath(checkboxes_label)]
            for box in range(list_categories):
                self.log.info(f"selecting the category {list_categories[box]} ")
                driver.find_elements_by_xpath(checkboxes_label)[box].click()
                self.scroll_down(driver)
                time.sleep(4)
                self.scroll_up(driver)
                self.course_links_main.append(pd.DataFrame({"category":list_categories[box],"Course_URL":self.fetch_course_links(driver)}, index=None))
                # uncheck the category
                driver.find_elements_by_xpath(checkboxes_label)[box].click()
            return self.course_links_main
        except Exception as e:
            self.log.exception(e)

    def get_course_categories_and_links(self):
        try:
            driver=self.set_chrome_options()
            self.open_url(driver)

            links_list=self.tick_categories(driver)
            self.log.info("List of course links received")
            links_df=pd.DataFrame()

            for each_df in links_list:
                links_df=pd.concat([links_df, each_df],ignore_index=True)
            if os.path.exists("Output"):
                self.log.info("The output folder exists saving the links to an excel")
                links_df.to_excel('Course_links.xlsx',sheet_name="Course_links",index=None)
            else:
                self.log.info("The output folder doesnt exists")
                self.log.info("Creating the output folder")
                os.mkdir("output")
                self.log.info("saving the links to an excel")
                links_df.to_excel('Course_links.xlsx',sheet_name="Course_links",index=None)
            return links_df
        except Exception as e:
            self.log.exception(e)

    def open_url(self, driver):
        try:
            self.set_chrome_options()
            self.log.info("opening the url")
            driver.get(self.url)
            driver.maximize_window()
            driver.implicitly_wait(10)
            course_link = '//*[@id="' + '__next"]/div[1]/nav/div[4]/div/a[1]'
            self.log.info("Goto Courses tab")
            driver.find_element_by_xpath(course_link).click()
            driver.refresh()
            time.sleep(5)
            # see more option
            self.log.info("See more Option")
            see_more_option = '//*[@id="' + '__next"]/div[1]/section[3]/div/div/div[1]/div[2]/div[1]/div[2]/div/span/i'
            driver.find_element_by_xpath(see_more_option).click()
        except Exception as e:
            self.log.exception(e)

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
            path = "chromedriver.exe"
            # Creates a new instance of the chrome driver.
            # Starts the service and then creates new instance of chrome driver.
            # Controls the ChromeDriver and allows you to drive the browser.
            driver = webdriver.Chrome(executable_path=path, options=chrome_options)

            return driver
        except Exception as e:
            self.log.exception(e)


sc=scrapper()
sc.get_course_categories_and_links()