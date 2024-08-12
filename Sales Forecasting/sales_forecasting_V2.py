import pandas as pd
import holidays

# Load the sales data from a CSV file
sales_data = pd.read_csv('sales_data.csv')

# Remove duplicates
sales_data.drop_duplicates(inplace=True)

# Fill missing values with the mean
sales_data.dropna(inplace=True)

# Encode categorical variables using one-hot encoding
sales_data = pd.get_dummies(sales_data, columns=['product'])

# Normalize the numerical variables
numerical_cols = ['sales']
sales_data[numerical_cols] = (sales_data[numerical_cols] - sales_data[numerical_cols].mean()) / sales_data[numerical_cols].std()

# Create new features based on existing ones
# Convert the 'date' column to datetime format
sales_data['date'] = pd.to_datetime(sales_data['date'])

# Extract month and day from the date
sales_data['month'] = sales_data['date'].dt.month
sales_data['day'] = sales_data['date'].dt.day

# Extract the name of the day of the week
sales_data['day_of_week'] = sales_data['date'].dt.day_name()

# Create a list of Colombian holidays for the relevant years
colombian_holidays = holidays.Colombia(years=sales_data['date'].dt.year.unique())

# Check if the date is a holiday
sales_data['is_holiday'] = sales_data['date'].isin(colombian_holidays)

# Display the updated dataframe
sales_data.head()