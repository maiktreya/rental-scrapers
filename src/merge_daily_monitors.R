# This script uses a Extract-Transform-Load approach to marge daily monitors into a single dataset and stores it into a single excel file for further analysis.

rm(list = ls())
gc(full = TRUE, verbose = TRUE)
library(data.table)
library(openxlsx)

# Example usage
source("src/etl_function.R") # import needed piping logic
data_path <- "out" # define path to data folder storing daily monitors
stacked_data <- stack_housing_data(data_path) # extract data from base files

# Create a new workbook
wb <- createWorkbook()

# Add each data.table to a separate sheet
addWorksheet(wb, "Airbnb Short-Term")
writeDataTable(wb, "Airbnb Short-Term", stacked_data$airbnb_short)

addWorksheet(wb, "Airbnb Med-Term")
writeDataTable(wb, "Airbnb Med-Term", stacked_data$airbnb_med)

addWorksheet(wb, "Airbnb Long-Term")
writeDataTable(wb, "Airbnb Long-Term", stacked_data$airbnb_long)

addWorksheet(wb, "Idealista Rent")
writeDataTable(wb, "Idealista Rent", stacked_data$idealista_rent)

addWorksheet(wb, "Idealista Sell")
writeDataTable(wb, "Idealista Sell", stacked_data$idealista_sell)

# Save the workbook
saveWorkbook(wb, "stacked_housing_data.xlsx", overwrite = TRUE)

# The XLSX file "stacked_housing_data.xlsx" is saved with each monitor in a separate sheet
