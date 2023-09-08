import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import tkinter as tk
from tkinter import simpledialog, messagebox
import re
import sqlite3

# Function to go through the browser and find the text element
def get_element_text(browser, xpath, wait_time=10):
    try:
        element = WebDriverWait(browser, wait_time).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return element.text
    except TimeoutException:
        return None


root = tk.Tk()
root.withdraw()  # This hides the root window

# Function to check if the date is in the correct format using regular expression   
def is_valid_date(date_str):
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

date = simpledialog.askstring("Input", "Input the date until you want to calculate using (yyyy-mm-dd):")

while not is_valid_date(date):
    messagebox.showerror("Error", "Please enter the date in yyyy-mm-dd format.")
    date = simpledialog.askstring("Input", "Input the date until you want to calculate using (yyyy-mm-dd):")

# Specific date until we will calculate the rewards 
specific_date = pd.to_datetime(f'{date}')
print(specific_date)
# Folder path
folder = 'C:\\Users\\Eni boy\\Desktop\\Web Srapping'

# Creating Excel file
writer1 = pd.ExcelWriter(folder + '\\' + f'Rewards{date}.xlsx')

# Read the excel with rewards
df = pd.read_excel('./Cantina_Royale.xlsx')

# Connect to the SQLite database. This will create a file "mydatabase.db" where the data will be stored
conn = sqlite3.connect('mydatabase.db')
cursor = conn.cursor()

# Drop the "Transactions" table if it exists
cursor.execute("DROP TABLE IF EXISTS Transactions;")
conn.commit()

# Filter rows that CRT is less than 0 
df = df[df['CRT'] >= 0]

# Convert the columns values to dates
df['Date'] = pd.to_datetime(df['Date'])

# Sort date by asc order
df_allLending = df.sort_values(by='Date', ascending=True)

# Now you can safely create the table without worrying about it existing
df_allLending.to_sql('Transactions', conn, index=False)

query = f"""
    SELECT * FROM Transactions 
    WHERE Label IN ('Direct lending', 'Staking', 'Player', 'Borrowing') 
    AND Date >= '{specific_date}'
"""

df_allLending = pd.read_sql(query, conn)

# Convert the column D'Date' values to dates
df_allLending['Date'] = pd.to_datetime(df_allLending['Date'])

#Printing the output from the database
print(df_allLending)
#Closing the connection to the databse
conn.close()

# The latest date in the Excel
latestDate = df['Date'].iloc[0]

#Difference -  days between lates date and the specific date
difference = (latestDate - specific_date).days

# Group by the result by NFT ID and calculate the sum of the CRT per NFT ID
result = df_allLending.groupby(['NFT ID','Label'])['CRT'].sum().reset_index()

# Rename the columns
result = result.rename(columns={'CRT':'Total rewards(in CRT)'})

# Setting lists for the data taken from the web scrapping
lenders = []
IDs = []
HashIDs = []
RarityClasses = []
Levels = []

# Getting unique NFT IDs
nft_ids = result['NFT ID']
uniqueIDs = list(dict.fromkeys(nft_ids))

#Define chrome driver exe path
chrome_driver_path = f'./chromedriver.exe'

# Initialize a single browser instance
ser = Service(chrome_driver_path)
chrome_options = webdriver.ChromeOptions()
browser = webdriver.Chrome(service=ser, options=chrome_options)

# Open and Maximize window only once
browser.maximize_window()

# Iterate through all unique ids in each web page 
for id in uniqueIDs:
    browser.get(f'https://cantina-corner.io/nft/{id}')
    
    nftID = get_element_text(browser, '/html/body/main/div[1]/div[2]/div/div/div[1]/h2')
    HashID = get_element_text(browser, '/html/body/main/div[1]/div[2]/div/div/div[1]/h1')
    
    # Try to get lender from various XPaths
    lender = get_element_text(browser, '/html/body/main/div[1]/div[2]/div/div/div[1]/div[2]', wait_time=1) or \
             get_element_text(browser, '/html/body/main/div[1]/div[2]/div/div/div[1]/div[2]/a', wait_time=1) or \
             get_element_text(browser, '/html/body/main/div[1]/div[2]/div/div/div[1]/div/a', wait_time=1)
    
    RarityClass = get_element_text(browser, '/html/body/main/div[1]/div[2]/div/div/div[1]/span', wait_time=3)
    level = get_element_text(browser, '/html/body/main/div[1]/div[2]/div/div/div[2]/div[1]/strong')

    # Appending the values to each list
    if nftID:
        IDs.append(nftID)
    if HashID:
        HashIDs.append(HashID)
    if lender:
        lenders.append(lender)
    if RarityClass:
        RarityClasses.append(RarityClass)
    if level:
        Levels.append(level)

# Close browser after loop
browser.quit()

#Creating the Dataframe from the Web page
web=(
 {
 "NFT ID": IDs,
 "NFT #ID": HashIDs,
 "Player/Lender/Public staking": lenders,
 "Rarity Class": RarityClasses,
 'Level': Levels
 })

dfWeb=pd.DataFrame(web)

#Merging the data from Web browser and Excel file
output = pd.merge(dfWeb,result, on='NFT ID')

#Webdriver settings
ser = Service(chrome_driver_path)
chrome_options = webdriver.ChromeOptions()
browser = webdriver.Chrome(service=ser, options=chrome_options)

# Open and Maximize window and opening the price chart
browser.maximize_window()
browser.get(f'https://www.coingecko.com/en/coins/cantina-royale')
browser.implicitly_wait(5)

#Locating CRT price 
if browser.find_element(By.XPATH, '/html/body/div[3]/main/div[1]/div[1]/div/div[1]/div[2]/div/div[1]/span[1]/span').is_displayed:
    #Locaing element as text
    CRT_price = browser.find_element(By.XPATH, '/html/body/div[3]/main/div[1]/div[1]/div/div[1]/div[2]/div/div[1]/span[1]/span').text

    # Close browser
    browser.quit()

#Remove the $ sign from the price to calculate the rewards
CRT_price = CRT_price[1:]

#Multiplying each row in the Column by the price
output['Total rewards in USD'] = output['Total rewards(in CRT)'].astype(float) * float(CRT_price)

#Sort the Dataframe based on column: 'Lending/Public staking'
output = output.sort_values(by=['Total rewards(in CRT)','Rarity Class','Level'])

#DataFrame for only Direct Lending
df_directLend = df_allLending[df_allLending['Label'] == 'Direct lending']

#Group by NFT ID and Label and count the CRT totall amount per NFT ID
df_CRTDirectResult = df_directLend.groupby(['NFT ID','Label'])['CRT'].sum().reset_index(name='CRT')

#Count the Games played per NFT ID
df_directLendResult = df_directLend.groupby(['NFT ID','Label'])['NFT ID'].count().reset_index(name='Games')

#Merge both Dataframes based on NFT ID and Label
df_directFinal = pd.merge(df_CRTDirectResult,df_directLendResult,on=['NFT ID','Label'])

#Calculate the average games per day
df_directFinal['AVG Games per day'] = df_directFinal['Games']/difference

#Calculate the average CRT earned per Game
df_directFinal['CRT per Game'] = df_directFinal['CRT']/df_directFinal['Games']

#Calculate the Average CRT earned per Day
df_directFinal['Average CRT per Day'] = df_directFinal['CRT']/difference

#DataFrame for only Player 
df_player =   df_allLending[df_allLending['Label'] == 'Player']

#Group by NFT ID and Label and count the CRT totall amount per NFT ID
df_CRTPlayerResult = df_player.groupby(['NFT ID','Label'])['CRT'].sum().reset_index(name='CRT')

#Count the Games played per NFT ID
df_playerResults = df_player.groupby(['NFT ID','Label'])['NFT ID'].count().reset_index(name='Games')

#Merge both Dataframes based on NFT ID and Label
df_playerFinal = pd.merge(df_CRTPlayerResult,df_playerResults,on=['NFT ID','Label'])

#Calculate the average games per day
df_playerFinal['AVG Games per day'] = df_playerFinal['Games']/difference

#Calculate the average CRT earned per Game
df_playerFinal['CRT per Game'] = df_playerFinal['CRT']/df_playerFinal['Games']

#Calculate the Average CRT earned per Day
df_playerFinal['Average CRT per Day'] = df_playerFinal['CRT']/difference

#DataFrame for Staking rewards
df_Staking =  df_allLending[df_allLending['Label'] == 'Staking']

#Calculate Total CRT Rewards
df_StakingResult = df_Staking.groupby(['NFT ID','Label'])['CRT'].sum().reset_index(name='CRT')

#Calculate the Average rewards per day
df_StakingResult['Average CRT per Day'] = df_StakingResult['CRT']/difference

#Concat the Direct Lending and Player DataFrames
df_concat = pd.concat([df_playerFinal, df_directFinal], ignore_index=True)

df_dailyRewards = df_allLending[df_allLending['Label'].isin(['Direct lending','Player','Borrowing'])]


#Get only unique dates
allDates = df_dailyRewards['Date'].dt.date.unique()

#result object
results = {}

#Iterate trough all unique dates
for date in allDates:
    #Match the equal dates
    filtered_df = df_dailyRewards[df_dailyRewards['Date'].dt.date == date]
    
    #Calculate the total rewards per NFT ID
    total_rewards = filtered_df.groupby(['NFT ID','Label'])['CRT'].sum()
    
    #For each date total rewards per NFT ID
    results[date] = total_rewards
    

#Fill the NaN boxes with 0
df_result = pd.DataFrame(results).fillna(0)

#DataFrames to Excel
#Main Rewards sheet for all rewards form Player, Direct Lending, Staking, and Borrowing
output.to_excel(writer1, sheet_name="Rewards", index=False)

#Sheet for Player rewards
df_playerFinal.to_excel(writer1, sheet_name="Player", index=False)

#Sheet for Direct Lending rewards
df_directFinal.to_excel(writer1, sheet_name="Direct Lending", index=False)

#Sheet for Staking rewards
df_StakingResult.to_excel(writer1, sheet_name="Public Staking", index=False)

#Sheet for daily rewards 
df_result.to_excel(writer1, sheet_name="Result", index=True)


# This graphic shows the rewards for all NFTs used in USD
plt.figure(figsize=[10,6])
plt.bar(output['NFT ID'], output['Total rewards in USD'])
plt.title('Общи награди в USD за всеки NFT')
plt.xlabel('NFT ID')
plt.ylabel('Общи награди (USD)')
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()

# Групиране по Rarity Class и изчисляване на общите награди и броя на NFT-та
rarity_class_summary = output.groupby('Rarity Class').agg(
    total_rewards=('Total rewards(in CRT)', 'sum'),
    count_nfts=('NFT ID', 'count')
).reset_index()

# Изчисляване на средните награди за всеки Rarity Class
rarity_class_summary['average_rewards'] = rarity_class_summary['total_rewards'] / rarity_class_summary['count_nfts']

# Пай графика за разпределение на средните награди според класа на рядкост
plt.pie(rarity_class_summary['average_rewards'], labels=rarity_class_summary['Rarity Class'], autopct='%1.1f%%')
plt.title('Разпределение на средните награди според класа на рядкост')
plt.show()


# Групиране по седмици и изчисление на сумата на наградите
weekly_rewards = df_Staking.groupby(pd.Grouper(key='Date', freq='W')).agg(total_rewards=('CRT', 'sum')).reset_index()

plt.figure(figsize=[15, 7])

# Стълбова графика
plt.bar(weekly_rewards['Date'], weekly_rewards['total_rewards'], color='skyblue')

plt.title('Общи награди по седмици за Staking')
plt.xlabel('Дата')
plt.ylabel('Общи награди (CRT)')
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()


#Изчисляване на седмичните печалби за Player, Direct Lending, Borrowing
average_rewards_per_week = df_dailyRewards.groupby(pd.Grouper(key='Date', freq='W'))['CRT'].sum().reset_index()

plt.figure(figsize=[15, 7])

# Стълбова графика
plt.bar(average_rewards_per_week['Date'], average_rewards_per_week['CRT'], color='skyblue', width=5)

plt.title('Общи награди по седмици за Direct lending, Borrowing и Player')
plt.xlabel('Дата')
plt.ylabel('Общи награди (CRT)')
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()



# Изследвания за бъдещи печалби

# Sort date by asc order and filter
df = df[df['Label'].isin(['Player','Direct Lending','Borrowing'])]
df_allLending = df.sort_values(by='Date',ascending=True)
df_allLending['Date'] = pd.to_datetime(df_allLending['Date'])
df_allLending['Date_ordinal'] = df_allLending['Date'].apply(lambda x: x.toordinal())

# Filter to show only the last 3 months
three_months_ago = df_allLending['Date'].max() - pd.DateOffset(months=3)
df_allLending = df_allLending[df_allLending['Date'] > three_months_ago]

# Обучение на линейната регресия
X = df_allLending[['Date_ordinal']]
y = df_allLending['CRT']
model = LinearRegression()
model.fit(X, y)

# Предвиждане на бъдещите стойности за следващите 14 дни
future_dates = [df_allLending['Date'].max() + pd.Timedelta(days=i) for i in range(1, 15)]
future_dates_ordinal = [d.toordinal() for d in future_dates]
future_rewards = model.predict(np.array(future_dates_ordinal).reshape(-1, 1))

forecast_df = pd.DataFrame({
    'Future Dates': future_dates,
    'Predicted Rewards': future_rewards
})

# Преименувайте колоните в forecast_df
forecast_df = forecast_df.rename(columns={"Future Dates": "Date", "Predicted Rewards": "CRT"})

# Обединете df_allLending и forecast_df
full_df = pd.concat([df_allLending, forecast_df], ignore_index=True)

# Продължете с визуализацията
plt.figure(figsize=(15, 6))

# Реални данни
plt.plot(df_allLending['Date'], df_allLending['CRT'], 'o-', label='Actual', color='blue')

# Прогнозирани данни
plt.plot(forecast_df['Date'], forecast_df['CRT'], 'x-', label='Forecast', color='green')

# Чертане на вертикална линия, показваща началото на прогнозата
plt.axvline(x=df_allLending['Date'].max(), color='red', linestyle='--', label='Start of Forecast')

plt.fill_between(forecast_df['Date'], forecast_df['CRT'], color='green', alpha=0.1) # Подчертаване на прогнозата

plt.title('Last 3 Months with 14 Day Forecast')
plt.legend(loc='upper left')
plt.xlabel('Date')
plt.ylabel('Rewards (CRT)')
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.tight_layout()
plt.show()

forecast_df.to_excel(writer1, sheet_name="Linear Reg Forecast", index=False)


### Holt Winthers algorithm(Triple Exponential Smoothing method)

# Convert to datetime and set as index
df = df[df['Label'].isin(['Player','Direct Lending','Borrowing'])]
df_allLending['Date'] = pd.to_datetime(df_allLending['Date'])
df_allLending.set_index('Date', inplace=True)

# Филтриране на df_allLending за последните три месеца (подобно на линейната регресия)
three_months_data = df_allLending[df_allLending.index > (df_allLending.index.max() - pd.DateOffset(months=3))]

# Apply Holt-Winters на филтрираните данни
model = ExponentialSmoothing(three_months_data['CRT'], trend='add', seasonal='add', seasonal_periods=7)
model_fit = model.fit()

# Прогноза за следващите 14 дни
forecast_steps = 14
forecast = model_fit.forecast(steps=forecast_steps)

# Преобразуване на прогнозата в DataFrame
forecast_dates = pd.date_range(start=three_months_data.index[-1] + pd.Timedelta(days=1), periods=forecast_steps, freq='D')
forecast_df = pd.DataFrame({
    'Date': forecast_dates,
    'Holt-Winters Rewards': forecast
})
forecast_df.set_index('Date', inplace=True)

# Визуализация
plt.figure(figsize=(15, 6))

# Реални данни
plt.plot(three_months_data['CRT'], 'o-', label='Actual', color='blue')

# Прогнозирани данни
plt.plot(forecast_df, 'x-', label='Forecast', color='red')

# Чертане на вертикална линия, показваща началото на прогнозата
plt.axvline(x=three_months_data.index[-1], color='green', linestyle='--', label='Start of Forecast')

plt.fill_between(forecast_df.index, forecast_df['Holt-Winters Rewards'], color='red', alpha=0.1) # Подчертаване на прогнозата

plt.title('Holt-Winters Forecast for the Last 3 Months with 2 Weeks Prediction')
plt.legend(loc='upper left')
plt.xlabel('Date')
plt.ylabel('Rewards (CRT)')
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.tight_layout()
plt.show()

# Показване на DataFrame с прогнозираните данни
print(forecast_df)
forecast_df.to_excel(writer1, sheet_name="Holt-Winters Forecast", index=True)


# Филтриране на df_allLending за последните три месеца
three_months_data = df_allLending[df_allLending.index > (df_allLending.index.max() - pd.DateOffset(months=3))]

linear_forecast_df = pd.DataFrame({
    'Date': future_dates,
    'Linear Predicted Rewards': future_rewards
})
linear_forecast_df.set_index('Date', inplace=True)

# Обединение на прогнозите от Holt-Winters и линейната регресия
combined_forecast = pd.merge(forecast_df, linear_forecast_df, left_index=True, right_index=True, how='inner')
combined_forecast['Difference (%)'] = ((combined_forecast['Holt-Winters Rewards'] - combined_forecast['Linear Predicted Rewards']) / combined_forecast['Linear Predicted Rewards']) * 100

# Визуализация
plt.figure(figsize=(15, 7))

# Реални данни
plt.plot(three_months_data['CRT'], 'o-', label='Actual', color='green', linewidth=2)

# Прогнозирани данни от Holt-Winters
plt.plot(combined_forecast['Holt-Winters Rewards'], 's-', label='Holt-Winters', color='red', linewidth=2)

# Прогнозирани данни от линейната регресия
plt.plot(combined_forecast['Linear Predicted Rewards'], 'x--', label='Linear Regression', color='blue', linewidth=2)

# Чертане на вертикална линия, показваща началото на прогнозата
plt.axvline(x=three_months_data.index[-1], color='grey', linestyle='--', label='Start of Forecast')

# Подчертаване на областта на прогнозата
plt.axvspan(combined_forecast.index[0], combined_forecast.index[-1], facecolor='yellow', alpha=0.1)

plt.title('Comparison of Predictions for the Next 14 Days')
plt.legend(loc='upper left')
plt.xlabel('Date')
plt.ylabel('Predicted Rewards')
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.tight_layout()
plt.show()

# Показване на обединената таблица с прогнози
print(combined_forecast)
combined_forecast.to_excel(writer1, sheet_name="Comparison Forecast", index=True)

writer1.close()





