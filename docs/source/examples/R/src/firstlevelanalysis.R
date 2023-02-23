#first level analysis




#get the helper functions
source(here("docs","source","examples","R","src","helpers.R"))

#the main function to run a single person analysis
single_sub_analysis = function(df,interoPost = NA, exteroPost = NA, bayesian = FALSE, model = NA){
  
  #check for NA's in the critical columns of the data:
  if(sum(is.na(df %>% select(ResponseMade, Decision,Confidence, ConfidenceRT, Confidence, Condition, listenBPM, responseBPM))) != 0){
    n_NA = sum(is.na(df %>% select(ResponseMade, Decision,Confidence, ConfidenceRT, Confidence, Condition, listenBPM, responseBPM)))
    print(paste("Number of NA's = ",n_NA," detected"))
  }
  #remove the NA's
  df1 = df %>% drop_na(ResponseMade, Decision,Confidence, ConfidenceRT, Confidence, Condition, listenBPM, responseBPM)
  
  
  
  #find number of modalities:
  n_mod = length(unique(df$Modality))
  
  if(n_mod>2){
    print("More than 2 modalities are not supported (yet)")
  }
  
  #give the resulting dataframe (main subject results a random id)
  id = runif(1, min=1, max=1000)
  #make the data frame:
  resultsdata = data.frame(ids = rep(id, n_mod))
  #create a folder to put the results:
  dir.create("results_sub")
  
  #getting the plots from the help function
  
  reactiontimeplot = reaction_time_plot(df,3,0.4,n_mod)
  stat = reactiontimeplot[[2]]
  
  #append the main statistics from the reaction time plot to the resulting dataframe
  resultsdata = cbind(resultsdata, stat)
  
  #get the reaction time plot where we exclude the legends.
  reactiontimeplot = reactiontimeplot[[1]]+guides(fill = "none")

  #get the citerion and d' and the table:
  stat = sum_stat(df)
  
  #append results
  resultsdata = cbind(resultsdata,stat[[2]])
  
  #use the dataframe with removed NA's
  #get confidence histogram plot
  confidenceplot = plot_confidence(df1,n_mod)
  
  #get mean accuracy
  results = get_mean_acc(df)
  
  #append results
  resultsdata = cbind(resultsdata,results)
  
  
  
  #get the intensityplot and remove legends and title
  intensityplot = intensity_plot(df)
  intensityplot = intensityplot+guides(fill = "none")+ggtitle(" ")
  
  #get interval plot:
  if(is.na(exteroPost[1]) == TRUE && is.na(interoPost[1]) == TRUE){
    intervalplot = ggplot() + theme_void()
  }
  if(is.na(exteroPost[1]) == TRUE && is.na(interoPost[1]) == FALSE){
    intervalplot = plot_interval(df,interoPost)
  }
  if(is.na(exteroPost[1]) == FALSE && is.na(interoPost[1]) == TRUE){
    intervalplot = plot_interval(df,exteroPost)
  }
  if(is.na(exteroPost[1]) == FALSE && is.na(interoPost[1]) == FALSE){
    intervalplot = plot_interval(df,exteroPost,interoPost)
  }

  #get analysis plot (alpha vs probability of answering more)
  analysisplot = analysis_plot(df)
  stats = analysisplot[[2]]
  
  #append results of this plot
  resultsdata = cbind(resultsdata,stats)
  
  analysisplot = analysisplot[[1]]+guides(fill = "none",linetype = "none",color = "none")

  #make the composit-plot with patchwork
  plot = (reactiontimeplot+confidenceplot)/(analysisplot+intensityplot+intervalplot)+plot_layout(nrow = 2)
  
  #save the plot:
  ggsave("results_sub/resultplot_basic.png",plot, width = 4000, height = 2200, units = "px")
  
  
  #if the bayesian analysis is selected:
  if(bayesian == TRUE){

    if(n_mod == 2){
      
      #run bayesian analysis on Extero and Intero and append the statistics to the dataframe (resultsdata)
      baysextero = baysiananalysis(df,"Extero",model)
      stats = baysextero[[4]]
  
      baysintero = baysiananalysis(df,"Intero",model)
      stats = rbind(stats,baysintero[[4]])
      
      resultsdata = cbind(resultsdata,stats)
      
      baysplot_ex=baysextero[[1]]+baysextero[[2]]+baysextero[[3]]+plot_layout(design = c(
        patchwork::area(1, 1,1,1),
        patchwork::area(1,2,1,2),
        patchwork::area(2,1,3,2)))
      
      baysplot_in = baysintero[[1]]+baysintero[[2]]+baysintero[[3]]+plot_layout(design = c(
        patchwork::area(1, 1,1,1),
        patchwork::area(1,2,1,2),
        patchwork::area(2,1,3,2)))
      
      baysplot=baysextero[[1]]+baysextero[[2]]+baysextero[[3]]+baysintero[[1]]+baysintero[[2]]+baysintero[[3]]+plot_layout(design = c(
      patchwork::area(1, 1,1,1),
      patchwork::area(1,2,1,2),
      patchwork::area(2,1,3,2),
      patchwork::area(1,3,1,3),
      patchwork::area(1, 4, 1, 4),
      patchwork::area(2,3,3,4)))
      
      #save the figures
      ggsave("results_sub/resultplot_bayse_intero.png",baysplot_in, width = 4000, height = 2200, units = "px")
      ggsave("results_sub/resultplot_bayse_extero.png",baysplot_ex, width = 4000, height = 2200, units = "px")
      ggsave("results_sub/resultplot_bayse.png",baysplot, width = 4000, height = 2200, units = "px")
      
      baysplot = list(baysplot_ex,baysplot_in,baysplot)
      }
    
    if(n_mod == 1){
      bayse = baysiananalysis(df,as.character(unique(df$Modality)),model)
      stats = bayse[[4]]
      resultsdata = cbind(resultsdata,stats)
      
      baysplot=bayse[[1]]+bayse[[2]]+bayse[[3]]+plot_layout(design = c(
        patchwork::area(1, 1,1,1),
        patchwork::area(1,2,1,2),
        patchwork::area(2,1,3,2)))
      ggsave("results_sub/resultplot_bayse.png",baysplot, width = 4000, height = 2200, units = "px")  
    }
    
    #delete all duplicate columns in the resulting dataframe
    resultsdata = resultsdata[!duplicated(as.list(resultsdata))]
    #give it sensisble rownames:
    rownames(resultsdata) <- 1:nrow(resultsdata)
    #save it
    write.csv(resultsdata, "results_sub/data.csv")
    
    return(list(rt_plot = reactiontimeplot,summary_stat = stat,conf_plot = confidenceplot,staircase_plot = intervalplot,histogram_plot = intensityplot,analysis_plot = analysisplot,concatenated_plot = plot, stats = resultsdata,bayesian_plot = baysplot))
    
    }
  #delete all duplicate columns in the resulting dataframe
  resultsdata = resultsdata[!duplicated(as.list(resultsdata))]
  #give it sensisble rownames:
  rownames(resultsdata) <- 1:nrow(resultsdata)
  #save it
  write.csv(resultsdata, "results_sub/data.csv")
  
  return(list(rt_plot = reactiontimeplot,summary_stat = stat, conf_plot = confidenceplot, staircase_plot = intervalplot,histogram_plot = intensityplot,analysis_plot = analysisplot, concatenated_plot = plot, stats = resultsdata))
}
  
  


  
study_analysis = function(path, bayesian,model){

  wd = getwd()
  sub_folders = list.dirs(path = path, full.names = TRUE,recursive = FALSE)
  
  combined_data = data.frame()
  for (i in 1:length(sub_folders)){
    
    setwd(sub_folders[i])
    
    filelist = list.files(pattern = "*.txt")
    
    if (!is.character(filelist)){
      print("To many text files")
    }
    
    data = read_csv(filelist[1])
    
    numpy_filelist = list.files(pattern = "*.npy")
    
    if (length(numpy_filelist) != 2){
      print("Not 2 numpy files")
    }
    
    exteroPost = np$load(numpy_filelist[str_detect(tolower(numpy_filelist), "extero")])
    interoPost = np$load(numpy_filelist[str_detect(tolower(numpy_filelist), "intero")])
    
    
    liste = single_sub_analysis(data, interoPost = interoPost, exteroPost = exteroPost, bayesian = bayesian,model = model)
    
    combined_data = rbind(combined_data,liste$stats)
    
  }
  setwd(wd)
  write.csv(combined_data,"resulting_dataframe.csv")
return(combined_data)  
}
  