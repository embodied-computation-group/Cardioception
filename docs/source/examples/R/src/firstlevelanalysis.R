# first level analysis




# get the helper functions
source(here("docs", "source", "examples", "R", "src", "helpers.R"))

# the main function to run a single person analysis
single_sub_analysis <- function(df, interoPost = NA, exteroPost = NA, bayesian = FALSE, model = NA, out) {
  # starting off finding the columns of interrest and making sure they are the right format!
  
  df$ResponseCorrect <- ifelse(df$ResponseCorrect == "", NA, df$ResponseCorrect)
  df$Decision <- ifelse(df$Decision == "", NA, df$Decision)
  
  df <- df %>%
    mutate(
      Decision = as.character(df$Decision),
      ConfidenceRT = as.numeric(df$ConfidenceRT),
      DecisionRT = as.numeric(df$DecisionRT),
      Confidence = as.numeric(df$Confidence),
      Condition = as.character(df$Condition),
      listenBPM = as.numeric(df$listenBPM),
      responseBPM = as.numeric(df$responseBPM),
      ResponseCorrect = as.numeric(as.factor(df$ResponseCorrect)) - 1,
      EstimatedThreshold = as.numeric(df$EstimatedThreshold),
      EstimatedSlope = as.numeric(df$EstimatedSlope),
    )
  
  # check for NA's in the critical columns of the data:
  # specify different ways of coding missing values:
  missing_pres <- c(NA, "na", "N/A", "NaN", NaN, "n/a")
  
  trials_missing <- df %>%
    select(Decision, Confidence, ConfidenceRT, Confidence, Condition, listenBPM, responseBPM, nTrials) %>%
    filter_all(any_vars(. %in% missing_pres)) %>%
    .$nTrials
  
  
  
  if (length(trials_missing) != 0) {
    print(paste("Number of NA's = ", length(trials_missing), " detected in trials : "))
    print(as.character(trials_missing))
  }
  
  # remove the NA's
  df1 <- df %>% filter(!nTrials %in% trials_missing)
  
  
  
  # find number of modalities:
  n_mod <- length(unique(df1$Modality))
  
  if (n_mod > 2) {
    print("More than 2 modalities are not supported (yet)")
  }
  
  ## Checking for an ID column
  if (is.null(df$id[1])) {
    # give the resulting dataframe (main subject results a random id)
    df$id <- round(runif(1, min = 1, max = 10000),0)
    # make the data frame:
    resultsdata <- data.frame(ids = rep(df$id[1], n_mod))
  } else {
    resultsdata <- data.frame(ids = rep(df$id[1], n_mod))
  }
  
  output_dir = paste0(out,"/results_sub",resultsdata$id[1])
  #create an index for if the directory exists such that we dont overwrite files:
  
  
  if(is.null(df$file[1])){
    df$file = round(runif(1,min = 1, max = 1000),0)
  }
  
  idx = df$file[1]
  
  
  # create a folder to put the results:
  if(!dir.exists(output_dir)){
    dir.create(output_dir)
  }
  # getting the plots from the help function
  
  reactiontimeplot <- reaction_time_plot(df, 3, 0.4, n_mod)
  stat <- reactiontimeplot[[2]]
  
  # append the main statistics from the reaction time plot to the resulting dataframe
  resultsdata <- cbind(resultsdata, stat)
  
  # get the reaction time plot where we exclude the legends.
  reactiontimeplot <- reactiontimeplot[[1]] + guides(fill = "none")
  
  # get the citerion and d' and the table:
  stat <- sum_stat(df)
  
  # append results
  resultsdata <- cbind(resultsdata, stat[[2]])
  
  # use the dataframe with removed NA's
  # get confidence histogram plot
  confidenceplot <- plot_confidence(df1, n_mod)
  
  # get mean accuracy
  results <- get_mean_acc(df)
  
  # append results
  resultsdata <- cbind(resultsdata, results)
  
  
  
  # get the intensityplot and remove legends and title
  intensityplot <- intensity_plot(df)
  intensityplot <- intensityplot + guides(fill = "none") + ggtitle(" ")
  
  # get interval plot:
  if (is.na(exteroPost[1]) == TRUE && is.na(interoPost[1]) == TRUE) {
    intervalplot <- ggplot() +
      theme_void()
  }
  if (is.na(exteroPost[1]) == TRUE && is.na(interoPost[1]) == FALSE) {
    intervalplot <- plot_interval(df1, interoPost)
  }
  if (is.na(exteroPost[1]) == FALSE && is.na(interoPost[1]) == TRUE) {
    intervalplot <- plot_interval(df1, exteroPost)
  }
  if (is.na(exteroPost[1]) == FALSE && is.na(interoPost[1]) == FALSE) {
    intervalplot <- plot_interval(df1, exteroPost, interoPost)
  }
  
  # get analysis plot (alpha vs probability of answering more)
  analysisplot <- analysis_plot(df)
  stats <- analysisplot[[2]]
  
  # append results of this plot
  resultsdata <- cbind(resultsdata, stats)
  
  analysisplot <- analysisplot[[1]] + guides(fill = "none", linetype = "none", color = "none")
  
  
  ### AUC
  AUC_plot = get_AUC(df1,bins = T,flem = T)$plot
  resultsdata = cbind(resultsdata, get_AUC(df1,bins = T, flem = T)$data)
  
  
  # make the composit-plot with patchwork
  plot <- (reactiontimeplot + confidenceplot + AUC_plot) / (analysisplot + intensityplot + intervalplot) + plot_layout(nrow = 2)
  
  # save the plot:
  ggsave(paste0(output_dir,"/resultplot_basic",idx,".png"), plot, width = 4000, height = 2200, units = "px")
  
  
  # if the bayesian analysis is selected:
  if (bayesian == TRUE) {
    if (n_mod == 2) {
      
        # run bayesian analysis on Extero and Intero and append the statistics to the dataframe (resultsdata)
        results = run_bayes_analysis(df1, model)
        
        # Combine stuff for stats and plots
        stats <- rbind(results[["Extero"]][["stats"]],results[["Intero"]][["stats"]])
        
        resultsdata <- cbind(resultsdata, stats)
        
        baysplot_ex <- results[["Extero"]][["chainplot"]] + results[["Extero"]][["traceplot"]] + results[["Extero"]][["bayseplot"]] +
          plot_layout(design = c(
          patchwork::area(1, 1, 1, 1),
          patchwork::area(1, 2, 1, 2),
          patchwork::area(2, 1, 3, 2)
        ))
        
        baysplot_in <- results[["Intero"]][["chainplot"]] + results[["Intero"]][["traceplot"]] + results[["Intero"]][["bayseplot"]] +
          plot_layout(design = c(
          patchwork::area(1, 1, 1, 1),
          patchwork::area(1, 2, 1, 2),
          patchwork::area(2, 1, 3, 2)
        ))
        
        # save the figures
        ggsave(paste0(output_dir,"/resultplot_bayse_intero",idx,".png"), baysplot_in, width = 4000, height = 2200, units = "px")
        ggsave(paste0(output_dir,"/resultplot_bayse_extero",idx,".png"), baysplot_ex, width = 4000, height = 2200, units = "px")
        
        bayesplot <- list(baysplot_ex, baysplot_in)
    }
    
    
    if (n_mod == 1) {
      
      modality = unique(df$Modality)
      # run bayesian analysis on Extero and Intero and append the statistics to the dataframe (resultsdata)
      results = run_bayes_analysis(df1, model)
      
      stats <- rbind(results[[modality]][["stats"]])
      
      resultsdata <- cbind(resultsdata, stats)
      
      bayesplot <- results[[modality]][["chainplot"]] + results[[modality]][["traceplot"]] + results[[modality]][["bayseplot"]] +
        plot_layout(design = c(
          patchwork::area(1, 1, 1, 1),
          patchwork::area(1, 2, 1, 2),
          patchwork::area(2, 1, 3, 2)
        ))
      
      # save the figures
      ggsave(paste0(output_dir,paste0("/resultplot_bayse_",modality),idx,".png"), bayesplot, width = 4000, height = 2200, units = "px")
      
      bayesplot <- list(bayesplot)
    }
    

      # delete all duplicate columns in the resulting dataframe
      
      resultsdata <- resultsdata[, !duplicated(colnames(resultsdata))]
      # give it sensisble rownames:
      rownames(resultsdata) <- 1:nrow(resultsdata)
      # save it
      write.csv(resultsdata, paste0(output_dir,"/data",idx,".csv"))
      
      return(list(rt_plot = reactiontimeplot, summary_stat = stat, conf_plot = confidenceplot,AUC_plot = AUC_plot, staircase_plot = intervalplot, histogram_plot = intensityplot, analysis_plot = analysisplot, concatenated_plot = plot, stats = resultsdata, bayesian_plot = bayesplot))
      
    
  }
  
  # delete all duplicate columns in the resulting dataframe
  resultsdata <- resultsdata[, !duplicated(colnames(resultsdata))]
  # give it sensisble rownames:
  rownames(resultsdata) <- 1:nrow(resultsdata)
  # save it
  write.csv(resultsdata, paste0(output_dir,"/data",idx,".csv"))
  
  return(list(rt_plot = reactiontimeplot, summary_stat = stat, conf_plot = confidenceplot,AUC_plot = AUC_plot, staircase_plot = intervalplot, histogram_plot = intensityplot, analysis_plot = analysisplot, concatenated_plot = plot, stats = resultsdata))
}





study_analysis <- function(path, bayesian, model, folder = T, out) {
  if (folder) {
    sub_folders <- list.dirs(path = path, full.names = TRUE, recursive = FALSE)
    print(paste0("found ", length(sub_folders), " directories"))
    
    combined_data <- data.frame()
    for (i in 1:length(sub_folders)) {
      
      filelist <- list.files(path =  paste0(sub_folders[i]), pattern = "*_final.txt")
      
      if (!is.character(filelist)) {
        print("To many text files with _final.txt")
      }
      
      if(is.na(filelist[1])){
        print(paste0("In the folder ", sub_folders[i], " there seems to be no _final.txt file this subject is therefore skipped"))
        next
      }
      
      data <- read_csv(paste0(sub_folders[i],"/",filelist[1]))
      
      data$id = gsub("^\\D*(\\d+).*", "\\1", filelist)
      file <- filelist
      data$file = file
      
      numpy_filelist <- list.files(path =  paste0(sub_folders[i]),pattern = "*.npy")
      
      if (length(numpy_filelist) != 2) {
        print("Not 2 numpy files")
      }
      
      numpy_filelist = paste0(sub_folders[i],"/",numpy_filelist)
      
      
      
      tryCatch(
        {
          exteroPost <- np$load(numpy_filelist[str_detect(tolower(numpy_filelist), "extero")])
          interoPost <- np$load(numpy_filelist[str_detect(tolower(numpy_filelist), "intero")])
          
        },
        error = function(err) {
          exteroPost <<- NA
          interoPost <<- NA
          print("No numpy files found")
        }
      )
      
      
      liste <- single_sub_analysis(data, interoPost = interoPost, exteroPost = exteroPost, bayesian = bayesian, model = model, out = out)
      
      combined_data <- rbind(combined_data, liste$stats %>% mutate(file = file))
      
    }
    
    write.csv(combined_data, paste0(out,"/resulting_dataframe.csv"))
  } else {
    sub_files <- list.files(path = path, full.names = TRUE, recursive = FALSE, pattern = "*final.txt")
    print(paste0("found ", length(sub_files), " files"))
    
    combined_data <- data.frame()
    for (i in 1:length(sub_files)) {
      print(paste0("Analyzing number ", i))
      
      
      if (!is.character(sub_files[i])) {
        print("To many text files")
      }
      
      data <- read_csv(sub_files[i])
      
      numpy_filelist <- list.files(pattern = "*.npy")
      
      
      data$id = gsub("^\\D*(\\d+).*", "\\1", sub_files[i])
      
      
      file <- basename(sub_files[i])
      data$file = file
      
      tryCatch(
        {
          exteroPost <- np$load(numpy_filelist[str_detect(tolower(numpy_filelist), "extero")])
          interoPost <- np$load(numpy_filelist[str_detect(tolower(numpy_filelist), "intero")])
        },
        error = function(err) {
          exteroPost <<- NA
          interoPost <<- NA
          print("No numpy files found")
        }
      )
      
      
      
      liste <- single_sub_analysis(data, interoPost = interoPost, exteroPost = exteroPost, bayesian = bayesian, model = model, out = out)
      
      combined_data <- rbind(combined_data, liste$stats %>% mutate(file = file))
      write.csv(combined_data, paste0(out,"/resulting_dataframe.csv"))
      
    }
    
  }
  
}
