#first level analysis

#importing libraries
pacman::p_load(tidyverse,ggdist,psycho,caret,patchwork, gt, cowplot, grid)

raincloud_theme = theme(
  text = element_text(size = 10),
  axis.title.x = element_text(size = 16),
  axis.title.y = element_text(size = 16),
  axis.text = element_text(size = 14),
  axis.text.x = element_text(angle = 45, vjust = 0.5),
  legend.title=element_text(size=16),
  legend.text=element_text(size=16),
  legend.position = "right",
  plot.title = element_text(lineheight=.8, face="bold", size = 16),
  panel.border = element_blank(),
  panel.grid.minor = element_blank(),
  panel.grid.major = element_blank(),
  panel.background = element_blank(),
  strip.background = element_rect(fill="white"),
  strip.text.x = element_text(size = 16),
  axis.line.x = element_line(colour = 'black', size=0.5, linetype='solid'),
  axis.line.y = element_line(colour = 'black', size=0.5, linetype='solid'))


source(file.path(working_directory,"src","helpers.R"))


single_sub_analysis = function(df,interoPost = NA, exteroPost = NA, theme = raincloud_theme, bayesian = FALSE, model = NA){
  
  if(sum(is.na(df %>% select(ResponseMade, Decision,Confidence, ConfidenceRT, Confidence, Condition, listenBPM, responseBPM))) != 0){
    
    n_NA = sum(is.na(df %>% select(ResponseMade, Decision,Confidence, ConfidenceRT, Confidence, Condition, listenBPM, responseBPM)))
    print(paste("NA's will be dropped from the analysis ",n_NA," detected"))
  }
  
  df = df %>% drop_na(ResponseMade, Decision,Confidence, ConfidenceRT, Confidence, Condition, listenBPM, responseBPM)
  
  
  
  #find number of modalities:
  n_mod = length(unique(df$Modality))
  
  if(n_mod>2){
    print("More than 2 modalities are not supported (yet)")
  }
  
  id = runif(1, min=1, max=1000)
  
  resultsdata = data.frame(ids = rep(id, n_mod))

  dir.create("results_sub")
  
  reactiontimeplot = reaction_time_plot(df,3,0.4,n_mod)
  stat = reactiontimeplot[[2]]
  resultsdata = cbind(resultsdata, stat)
  
  reactiontimeplot = reactiontimeplot[[1]]
  reactiontimeplot = reactiontimeplot+guides(fill = "none")
  
  
  stat = sum_stat(df)
  
  resultsdata = cbind(resultsdata,stat[[2]])
  
  confidenceplot = plot_confidence(df,n_mod)
  
  results = get_mean_acc(df)
  
  resultsdata = cbind(resultsdata,results)
  
  
  
  
  intensityplot = intensity_plot(df)
  intensityplot = intensityplot+guides(fill = "none")+ggtitle(" ")
  
  
  if(is.na(exteroPost[1]) == TRUE || is.na(interoPost) == TRUE){
    intervalplot = ggplot() + theme_void()
  }
  if(is.na(exteroPost) == TRUE && is.na(interoPost) == FALSE){
    intervalplot = plot_interval(df,interoPost)
  }
  if(is.na(exteroPost) == FALSE && is.na(interoPost) == TRUE){
    intervalplot = plot_interval(df,exteroPost)
  }
  else{
    intervalplot = plot_interval(df,exteroPost,interoPost)
  }

  
  analysisplot = analysis_plot(df)
  stats = analysisplot[[2]]
  resultsdata = cbind(resultsdata,stats)
  
  analysisplot = analysisplot[[1]]
  analysisplot = analysisplot+guides(fill = "none",linetype = "none",color = "none")
  
  
  plot = (reactiontimeplot+confidenceplot)/(analysisplot+intensityplot+intervalplot)+plot_layout(nrow = 2)
  
  ggsave("results_sub/resultplot_basic.png",plot, width = 4000, height = 2200, units = "px")
  
  
  
  if(bayesian == TRUE){
    library(posterior)
    library(rstan)
    library(cmdstanr)
    library(bayesplot)
    
    
    if(n_mod == 2){
      
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
      
      ggsave("results_sub/resultplot_bayse_intero.png",baysplot_in, width = 4000, height = 2200, units = "px")
      ggsave("results_sub/resultplot_bayse_extero.png",baysplot_ex, width = 4000, height = 2200, units = "px")
      ggsave("results_sub/resultplot_bayse.png",baysplot, width = 4000, height = 2200, units = "px")
      
      baysplot = list(baysplot_ex,baysplot_in,baysplot)
      }
    
    if(n_mod == 1){
      bayse = baysiananalysis(df,as.character(unique(df$Modality)),model)
      stats = bayse[[4]]
      
      
      baysplot=bayse[[1]]+bayse[[2]]+bayse[[3]]+plot_layout(design = c(
        patchwork::area(1, 1,1,1),
        patchwork::area(1,2,1,2),
        patchwork::area(2,1,3,2)))
      ggsave("results_sub/resultplot_bayse.png",baysplot, width = 4000, height = 2200, units = "px")  
    }
    
    
    resultsdata = resultsdata[!duplicated(as.list(resultsdata))]
    rownames(resultsdata) <- 1:nrow(resultsdata)
    write.csv(resultsdata, "results_sub/data.csv")
    
    return(list(rt_plot = reactiontimeplot,summary_stat = stat,conf_plot = confidenceplot,staircase_plot = intervalplot,histogram_plot = intensityplot,analysis_plot = analysisplot,concatenated_plot = plot, stats = resultsdata,bayesian_plot = baysplot))
    
    }
  
  resultsdata = resultsdata[!duplicated(as.list(resultsdata))]
  rownames(resultsdata) <- 1:nrow(resultsdata)
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
  