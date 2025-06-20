# This script uses a Extract-Transform-Load approach to marge daily monitors into a single dataset and stores it into a single excel file for further analysis.

rm(list = ls())
gc(full = TRUE, verbose = TRUE)
library(data.table)
library(openxlsx)

# Example usage
source("src/etl_function.R") # import needed piping logic
data_path <- "out" # define path to data folder storing daily monitors
stacked_data <- stack_housing_data(data_path) # extract data from base files

# Remove empty data.tables from the list
stacked_data <- stacked_data[sapply(stacked_data, function(x) nrow(x) > 0)]

# Check if there are any data.tables left after filtering
if (length(stacked_data) == 0) stop("No non-empty data.tables found.")

# coerce to numeric Airbnb price columns & drop properties outside target city
for (i in 1:3) {
    stacked_data[[i]][, price := as.numeric(gsub("[^0-9.]", "", price_with_tax))][, price_with_tax := NULL]
    stacked_data[[i]] <- stacked_data[[i]][property_title %like% "Segovia", ]
}

# Create a new workbook
wb <- createWorkbook()
# Add each non-empty data.table to a separate sheet
if ("airbnb_short" %in% names(stacked_data)) {
    addWorksheet(wb, "Airbnb Short-Term")
    writeData(wb, "Airbnb Short-Term", stacked_data$airbnb_short)
}
if ("airbnb_med" %in% names(stacked_data)) {
    addWorksheet(wb, "Airbnb Med-Term")
    writeData(wb, "Airbnb Med-Term", stacked_data$airbnb_med)
}
if ("airbnb_long" %in% names(stacked_data)) {
    addWorksheet(wb, "Airbnb Long-Term")
    writeData(wb, "Airbnb Long-Term", stacked_data$airbnb_long)
}
if ("idealista_rent" %in% names(stacked_data)) {
    addWorksheet(wb, "Idealista Buy")
    writeData(wb, "Idealista Buy", stacked_data$idealista_rent)
}
if ("idealista_sell" %in% names(stacked_data)) {
    addWorksheet(wb, "Idealista Rent")
    writeData(wb, "Idealista Rent", stacked_data$idealista_sell)
}

# Save the workbook
saveWorkbook(wb, "stacked_housing_data.xlsx", overwrite = TRUE)

# The XLSX file "stacked_housing_data.xlsx" is saved with each monitor in a separate sheet
