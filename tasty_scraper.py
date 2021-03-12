import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import selenium
from selenium import webdriver
import subprocess
from pathlib import Path
import time


def tasty_scrape(search, rec_type="recipe"):
    '''
    scrapes tasty.co for recipes matching *search*
    RETURNS DataFrame of:
        'href': 
            rec_type=="all" ---> all recipe links on page
            rec_type=="recipe" ---> all singular recipes on page
            rec_type=="compilation" ---> all recipe compilations on page
        'title':
            title of link
        'rectype':
            link type (compilation or recipe)
    '''
    # selenium driver setup
    print("retrieving webpage...")
    options = webdriver.chrome.options.Options()
    options.add_argument("--headless")
    node_modules_bin = subprocess.run(
        ["npm", "bin"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True
    )
    node_modules_bin_path = node_modules_bin.stdout.strip()
    chromedriver_path = Path(node_modules_bin_path) / "chromedriver"

    driver = selenium.webdriver.Chrome(
        options=options,
        executable_path=str(chromedriver_path),
    )
    driver.implicitly_wait(1)
    url = "https://tasty.co/search?q=" + search
    driver.get(url)

    # click "see more" button repeatedly
    print("clicking buttons...")
    bttndiv = driver.find_elements_by_xpath("//div[@class='show-more']")
    while (bttndiv):
        bttn = bttndiv[0].find_elements_by_tag_name('button')[0]
        bttn.click()
        time.sleep(0.2)
        bttndiv = driver.find_elements_by_xpath("//div[@class='show-more']")

    # compile all recipe data
    print("getting all links...")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    all_links = soup.find_all('a', class_='feed-item')
    data = {
        'href': [],
        'title': [],
        'rectype': [],
    }
    for link in all_links:
        ttl = link.find('div', class_='feed-item__title').text
        href = link['href']
        rtype = href.split('/')[1]
        if rec_type == 'all' or rtype == rec_type:
            url = "https://tasty.co" + href
            data['href'].append(url)
            data['title'].append(ttl)
            data['rectype'].append(rtype)

    return pd.DataFrame(data)


def tasty_recipe_scraper(url):
    '''
    INPUT: url of recipe to be scraped
    OUTPUT: dictionary of recipe's info
    '''
    recipe_page = requests.get(url)
    soup = BeautifulSoup(recipe_page.text, 'html.parser')
    info = {
        'title': '',
        'link': url,
        'score': None,
        'total_time': None,
        'prep': None,
        'cook': None,
        'num_ing': 0,
        'num_steps': 0
    }
    title_element = soup.find('h1', class_='recipe-name')
    if title_element:
        info['title'] = title_element.text
    scoretext = soup.find('h4', class_='tips-score-heading')
    if scoretext:
        info['score'] = int(scoretext.text.split('%')[0])
    times = soup.find_all('div', class_='recipe-time')
    if times:
        info['total_time'] = times[0].find('p').text
        info['prep'] = times[1].find('p').text
        info['cook'] = times[2].find('p').text
    ingredients = soup.find_all('li', class_='ingredient')
    info['num_ing'] = len(ingredients)
    steps = soup.find('ol', class_='prep-steps').find_all('li')
    info['num_steps'] = len(steps)
    return info


def tasty_compilation_scraper(url):
    '''
    INPUT: URL for a recipe compilation page
    OUTPUT: DataFrame with recipe info 
            compatible with scrape_all_recipes.all_recipe_info
    '''
    all_recipe_info = pd.DataFrame({
        'title': [],
        'link': [],
        'score': [],
        'total_time': [],
        'prep': [],
        'cook': [],
        'num_ing': [],
        'num_steps': []
    })
    comp_page = requests.get(url)
    soup = BeautifulSoup(comp_page.text, 'html.parser')
    all_recipes = soup.find_all('a', class_='feed-item')
    for recipe in all_recipes:
        url = "https://tasty.co" + recipe['href']
        info = tasty_recipe_scraper(url)
        all_recipe_info = all_recipe_info.append(info, ignore_index=True)
    return all_recipe_info


def scrape_all_comps(compdf):
    '''
    TODO: scrape all compilations in compdf
    scrapes each compilation page in DataFrame compdf
    returns DataFrame with all recipe info
    '''
    all_recipe_info = pd.DataFrame({
        'title': [],
        'link': [],
        'score': [],
        'total_time': [],
        'prep': [],
        'cook': [],
        'num_ing': [],
        'num_steps': []
    })
    for index, row in compdf.iterrows():
        info = tasty_compilation_scraper(row['href'])
        all_recipe_info = all_recipe_info.append(info, ignore_index=True)
    return all_recipe_info


def scrape_all_recipes(recipedf):
    '''
    scrapes each recipe page in DataFrame recipedf
    returns DataFrame with all recipe info
    '''
    all_recipe_info = pd.DataFrame({
        'title': [],
        'link': [],
        'score': [],
        'total_time': [],
        'prep': [],
        'cook': [],
        'num_ing': [],
        'num_steps': []
    })
    for index, row in recipedf.iterrows():
        info = tasty_recipe_scraper(row['href'])
        all_recipe_info = all_recipe_info.append(info, ignore_index=True)
    return all_recipe_info


def scrape_all_types(alldf):
    '''
    TODO: scrape all types of recipes in alldf
    scrapes each compilation or recipe page in DataFrame alldf
    returns DataFrame with all recipe info
    '''
    all_recipe_info = pd.DataFrame({
        'title': [],
        'link': [],
        'score': [],
        'total_time': [],
        'prep': [],
        'cook': [],
        'num_ing': [],
        'num_steps': []
    })
    for index, row in alldf.iterrows():
        if row['rectype'] == 'recipe':
            info = tasty_recipe_scraper(row['href'])
            all_recipe_info = all_recipe_info.append(info, ignore_index=True)
        elif row['rectype'] == 'compilation':
            info = tasty_compilation_scraper(row['href'])
            all_recipe_info = all_recipe_info.append(info, ignore_index=True)
        info = tasty_compilation_scraper(row['href'])
        all_recipe_info = all_recipe_info.append(info, ignore_index=True)
    return all_recipe_info


def tasty_recipes(search, rectype='recipe', sortcol=None):
    '''
    wrapper function for all tasty scraping
    searches tasty.co for all recipes related to search
    returns a duplicate-free DataFrame of all rec_type recipes,
        sorted on sortcol if provided
    rectype: {'recipe', 'compilation', 'all'}
    sortcol: {'title', 'link', 'score', 'total_time', 'prep', 'cook', 'num_ing', 'num_steps'}
    '''
    recipedf = scrape_all_types(tasty_scrape(search, rec_type=rectype))
    recipedf.drop_duplicates(subset="link", keep="first", inplace=True)
    if sortcol:
        recipedf.sort_values(sortcol, inplace=True)
