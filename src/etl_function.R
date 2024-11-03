# Load necessary libraries
library(data.table, quietly = TRUE)

# Define the function to stack daily observations
stack_housing_data <- function(data_path) {
    # List all CSV files in the folder
    csv_files <- list.files(data_path, pattern = "\\.csv$", full.names = TRUE)

    # Initialize empty lists to store the stacked data.tables
    airbnb_short <- list()
    airbnb_med <- list()
    airbnb_long <- list()
    idealista_rent <- list()
    idealista_sell <- list()

    # Loop through each file and classify based on the sequence
    for (file in csv_files) {
        # Extract the timestamp from the file name
        timestamp <- gsub(".*_(\\d{8})_.*\\.csv", "\\1", file)
        date <- as.Date(timestamp, format = "%Y%m%d")

        # Load the data
        dt <- fread(file)

        # Identify the monitor type based on file order and add the date column
        dt[, date := date]

        if (grepl("airbnb", file, ignore.case = TRUE)) {
            if (length(airbnb_short) == length(airbnb_med) &&
                length(airbnb_med) == length(airbnb_long)) {
                airbnb_short <- append(airbnb_short, list(dt))
            } else if (length(airbnb_med) == length(airbnb_long)) {
                airbnb_med <- append(airbnb_med, list(dt))
            } else {
                airbnb_long <- append(airbnb_long, list(dt))
            }
        } else if (grepl("idealista", file, ignore.case = TRUE)) {
            if (length(idealista_rent) == length(idealista_sell)) {
                idealista_rent <- append(idealista_rent, list(dt))
            } else {
                idealista_sell <- append(idealista_sell, list(dt))
            }
        }
    }

    # Combine the lists into single data.tables
    airbnb_short_dt <- rbindlist(airbnb_short, use.names = TRUE, fill = TRUE)
    airbnb_med_dt <- rbindlist(airbnb_med, use.names = TRUE, fill = TRUE)
    airbnb_long_dt <- rbindlist(airbnb_long, use.names = TRUE, fill = TRUE)
    idealista_rent_dt <- rbindlist(idealista_rent, use.names = TRUE, fill = TRUE)
    idealista_sell_dt <- rbindlist(idealista_sell, use.names = TRUE, fill = TRUE)

    # Return the result as a list of stacked data.tables
    return(list(
        airbnb_short = airbnb_short_dt,
        airbnb_med = airbnb_med_dt,
        airbnb_long = airbnb_long_dt,
        idealista_rent = idealista_rent_dt,
        idealista_sell = idealista_sell_dt
    ))
}
