from Scrapping_operations.webscrapper import scrapper

sc = scrapper()
df = sc.get_course_categories_and_links()
print(df)
sc.get_course_data_summary(list(df['Course_URL'][0:2]))
