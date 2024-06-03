# helper functions:


# function that makes the reaction time plot:
# Arguments:
# df = dataframe
# spacing_cond the spacing between the conditions in the plot
# spacing_corr the spacing between the correct and incorrect trials
# n_mod the number of modalities in the dataframe.
reaction_time_plot <- function(df, spacing_cond, spacing_corr, n_mod) {
  # first plot of Reaction time on Modality, accuracy and whether it was the Decision or the confidence rating:
  # spacing between the Intero and Extero:
  s <- spacing_cond
  # space between the correct incorrect:
  sc <- spacing_corr
  # colors
  col <- c("#5f9e6e", "#b55d60")
  
  # first part is modifying the data frame: Removing Nan trials, making the data frame longer and then renaming variables.
  df1 <- df %>%
    pivot_longer(cols = c(DecisionRT, ConfidenceRT)) %>%
    rename(Responsetime = value) %>%
    mutate(
      ResponseCorrect = ifelse(ResponseCorrect == 0, "Incorrect", "Correct"),
      name = as.factor(name),
      name = factor(name, labels = c("Confidence", "Decision")),
      name = relevel(name, ref = "Decision"),
      Modalityx = as.numeric(as.factor(Modality))
    )
  
  if (n_mod == 2) {
    plot <- df1 %>%
      # The plotting
      ggplot(aes(y = Responsetime, x = Modalityx, fill = ResponseCorrect, col = ResponseCorrect)) +
      # the distributions
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Correct" & Modalityx == 1), aes(x = Modalityx * s + sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "right") +
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Correct" & Modalityx == 2), aes(x = Modalityx * s + sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "right") +
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Incorrect" & Modalityx == 1), aes(x = Modalityx * s - sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "left") +
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Incorrect" & Modalityx == 2), aes(x = Modalityx * s - sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "left") +
      # the points
      geom_point(data = df1 %>% filter(ResponseCorrect == "Correct"), aes(y = Responsetime, x = Modalityx * s + sc / 2), position = position_jitter(width = .15), size = 1, alpha = 0.8) +
      geom_point(data = df1 %>% filter(ResponseCorrect == "Incorrect"), aes(y = Responsetime, x = Modalityx * s - sc / 2), position = position_jitter(width = .15), size = 1, alpha = 0.8) +
      facet_wrap(~name, scales = "free_y") +
      scale_color_brewer(palette = "Spectral") +
      scale_fill_brewer(palette = "Spectral") +
      ylab(label = "Response Time (s)") +
      guides(color = "none", alpha = "none") +
      xlab(label = "") +
      guides(fill = guide_legend(title = NULL)) +
      scale_fill_manual(values = col) +
      scale_color_manual(values = col) +
      scale_x_continuous(breaks = c(s, s * 2), labels = c("Extero", "Intero")) +
      theme(
        text = element_text(size = 10),
        axis.title.x = element_text(size = 16),
        axis.title.y = element_text(size = 16),
        axis.text = element_text(size = 14),
        axis.text.x = element_text(angle = 45, vjust = 0.5),
        legend.title = element_text(size = 16),
        legend.text = element_text(size = 16),
        legend.position = "right",
        plot.title = element_text(lineheight = .8, face = "bold", size = 16),
        panel.border = element_blank(),
        panel.grid.minor = element_blank(),
        panel.grid.major = element_blank(),
        panel.background = element_blank(),
        strip.background = element_rect(fill = "white"),
        strip.text.x = element_text(size = 16),
        axis.line.x = element_line(colour = "black", size = 0.5, linetype = "solid"),
        axis.line.y = element_line(colour = "black", size = 0.5, linetype = "solid")
      )
  } else {
    plot <- df1 %>%
      # The plotting
      ggplot(aes(y = Responsetime, x = Modalityx, fill = ResponseCorrect, col = ResponseCorrect)) +
      # the distributions
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Correct" & Modalityx == 1), aes(x = Modalityx * s + sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "right") +
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Correct" & Modalityx == 2), aes(x = Modalityx * s + sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "right") +
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Incorrect" & Modalityx == 1), aes(x = Modalityx * s - sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "left") +
      ggdist::stat_halfeye(data = df1 %>% filter(ResponseCorrect == "Incorrect" & Modalityx == 2), aes(x = Modalityx * s - sc, y = Responsetime, alpha = 0.9, scale = 0.7), side = "left") +
      # the points
      geom_point(data = df1 %>% filter(ResponseCorrect == "Correct"), aes(y = Responsetime, x = Modalityx * s + sc / 2), position = position_jitter(width = .15), size = 1, alpha = 0.8) +
      geom_point(data = df1 %>% filter(ResponseCorrect == "Incorrect"), aes(y = Responsetime, x = Modalityx * s - sc / 2), position = position_jitter(width = .15), size = 1, alpha = 0.8) +
      scale_color_brewer(palette = "Spectral") +
      scale_fill_brewer(palette = "Spectral") +
      ylab(label = "Response Time (s)") +
      guides(color = "none", alpha = "none") +
      xlab(label = "") +
      guides(fill = guide_legend(title = NULL)) +
      scale_fill_manual(values = col) +
      scale_color_manual(values = col) +
      scale_x_continuous(breaks = c(s), labels = c(as.character(unique(df$Modality)))) +
      theme(
        text = element_text(size = 10),
        axis.title.x = element_text(size = 16),
        axis.title.y = element_text(size = 16),
        axis.text = element_text(size = 14),
        axis.text.x = element_text(angle = 45, vjust = 0.5),
        legend.title = element_text(size = 16),
        legend.text = element_text(size = 16),
        legend.position = "right",
        plot.title = element_text(lineheight = .8, face = "bold", size = 16),
        panel.border = element_blank(),
        panel.grid.minor = element_blank(),
        panel.grid.major = element_blank(),
        panel.background = element_blank(),
        strip.background = element_rect(fill = "white"),
        strip.text.x = element_text(size = 16),
        axis.line.x = element_line(colour = "black", size = 0.5, linetype = "solid"),
        axis.line.y = element_line(colour = "black", size = 0.5, linetype = "solid")
      )
  }
  
  results <- df %>%
    group_by(Modality) %>%
    summarize(median_decisionRT = median(DecisionRT, na.rm = T), median_confidenceRT = median(ConfidenceRT, na.rm = T)) %>%
    rename(condition = Modality)
  
  
  return(list(plot, results))
}



# Function to get the summary statistics for a dataframe df:
sum_stat <- function(df) {
  # getting d' and the criterion for both conditions
  df_stat <- data.frame(NULL)
  for (i in unique(df$Modality)) {
    # making data frame with the Morality and creating stimuli and response column
    this_df <- df %>%
      filter(Modality == i) %>%
      mutate(stimuli = as.factor(responseBPM > listenBPM), Responses = as.factor(Decision == "More"))
    
    # making a Confusion Matrix to get hits (hit),correct rejections (cr), misses (miss), false accepted (fa)
    con <- confusionMatrix(this_df$stimuli, this_df$Responses)
    cr <- con$table[1, 1]
    hit <- con$table[2, 2]
    fa <- con$table[1, 2]
    miss <- con$table[2, 1]
    
    # getting d' and citerion from dprime function
    result <- dprime(hit, fa, miss, cr)
    
    # printing result
    print(paste("In the", i, "condition d-primne is", round(result$dprime, 2)))
    print(paste("In the", i, "condition criterion is", round(result$c, 2)))
    
    result$beta <- NULL
    result$aprime <- NULL
    result$bppd <- NULL
    
    df_stat <- rbind(df_stat, result)
  }
  # renameing and making it to a format that makes sense in gttable
  df_stat <- df_stat %>% rename(Criterion = c)
  rownames(df_stat) <- c(unique(df$Modality))
  df_stat$condition <- c(unique(df$Modality))
  
  # retun the table and the critical data (d' and citerion)
  gttable <- df_stat %>%
    gt(rowname_col = "condition") %>%
    tab_header(
      title = md("**dprime and criterion for conditions**")
    ) %>%
    tab_stubhead(label = md("**Condition**"))
  returns <- list(gttable, df_stat)
  
  return(returns)
}


# function to make bins (equvilent of python (metadpy-version)
discretebins <- function(df, nbins) {
  temp <- list()
  out <- list()
  
  quan <- quantile(df$Confidence, probs = seq(0, 1, length.out = nbins + 1))
  if ((quan[1] == quan[2]) & (quan[nbins - 1] == quan[nbins])) {
    stop("The resulting rating scale contains a lot of identical values and cannot be further analyzed")
  }
  
  
  if (quan[nbins - 1] == quan[nbins]) {
    print("Correcting for bias in high confidence ratings")
    hiConf <- tail(quan, n = 1)
    quan <- quantile(df$Confidence[df$Confidence != hiConf], probs = seq(0, 1, length.out = nbins + 1))
    for (b in 1:(length(quan) - 1)) {
      temp[[b]] <- (df$Confidence >= quan[b]) & (df$Confidence <= quan[b + 1])
    }
    # temp[length(quan)-1][[1]] = (df$Confidence == hiConf)
    out[["quan"]] <- quan
    out[["hiconf"]] <- hiConf
    out[["rebin"]] <- 1
  }
  
  
  if (quan[1] == quan[2]) {
    print("Correction for bias in low confidence ratings")
    lowConf <- tail(quan, n = 1)
    quan <- quantile(df$Confidence[df$Confidence != lowConf], probs = seq(0, 1, length.out = nbins + 1))
    for (b in 2:(length(quan))) {
      temp[[b]] <- (df$Confidence >= quan[b - 1]) & (df$Confidence <= quan[b])
    }
    # temp[length(quan)](df$Confidence == lowConf)
    out[["quan"]] <- quan
    out[["lowConf"]] <- lowConf
    out[["rebin"]] <- 1
  } else {
    for (b in 1:(length(quan) - 1)) {
      temp[[b]] <- (df$Confidence >= quan[b]) & (df$Confidence <= quan[b + 1])
    }
    out[["quan"]] <- quan
    out[["rebin"]] <- 0
  }
  ratings <- array(0, dim = length(df$Confidence))
  for (b in 1:nbins) {
    ratings[temp[[b]]] <- b
  }
  
  
  return(list(ratings, out))
}


# copy function of metadpy trials2count
trials2counts <- function(stimID, response, rating, nRatings, padAmount = 0, padCells = 0) {
  nR_S1 <- list()
  nR_S2 <- list()
  
  if (padAmount == 0) {
    padAmount <- 1 / (2 * nRatings)
  }
  # S1 responses
  for (r in nRatings:1) {
    cs1 <- 0
    cs2 <- 0
    for (i in 1:length(stimID)) {
      s <- stimID[i]
      x <- response[i]
      y <- rating[i]
      
      if ((s == 0) & (x == 0) & (y == r)) {
        (cs1 <- cs1 + 1)
      }
      if ((s == 1) & (x == 0) & (y == r)) {
        (cs2 <- cs2 + 1)
      }
    }
    nR_S1 <- append(nR_S1, cs1)
    nR_S2 <- append(nR_S2, cs2)
  }
  
  # S2 responses
  for (r in 1:nRatings) {
    cs1 <- 0
    cs2 <- 0
    for (i in 1:length(stimID)) {
      s <- stimID[i]
      x <- response[i]
      y <- rating[i]
      
      if ((s == 0) & (x == 1) & (y == r)) {
        (cs1 <- cs1 + 1)
      }
      if ((s == 1) & (x == 1) & (y == r)) {
        (cs2 <- cs2 + 1)
      }
    }
    nR_S1 <- append(nR_S1, cs1)
    nR_S2 <- append(nR_S2, cs2)
  }
  
  
  # pad response counts to avoid zeros
  nR_S1 <- as.numeric(nR_S1)
  nR_S2 <- as.numeric(nR_S2)
  if (padCells == 1) {
    nR_S1 <- lapply(nR_S1, FUN = function(x) x + padAmount)
    nR_S2 <- lapply(nR_S2, FUN = function(x) x + padAmount)
  }
  
  # Combine into lists
  newlist <- list(nR_S1, nR_S2)
  return(newlist)
}

# helper function to get the Correct and incorrect proportion (in the bins)
plot_conf <- function(srs) {
  if (length(srs[[1]]) != length(srs[[2]])) {
    stop("nR_S1 and nR_S2 should have same length")
  }
  
  nRratings <- length(srs[[1]]) / 2
  obsCount <- srs[[1]] + rev(srs[[2]])
  C_prop_data <- rev(obsCount[1:nRratings]) / sum(obsCount[1:nRratings])
  I_prop_data <- obsCount[(nRratings + 1):length(obsCount)] / sum(obsCount[(nRratings + 1):length(obsCount)])
  
  return(list(C_prop_data, I_prop_data))
}


# helper function to reorganize a dataframe such that plot_confidence can make a histogram of the confidence ratings.
get_df <- function(df, modality) {
  df <- df %>%
    filter(Modality == modality) %>%
    mutate(ResponseCorrect = ifelse(ResponseCorrect == 1, "Correct", "InCorrect"),
           stimuli = as.numeric(Alpha > 0),
           Modality = as.factor(Modality),
           reponse = as.factor(as.numeric((Decision == "More")))) %>%
    ungroup()
  
  df$Confidence_bin <- discretebins(df %>% filter(Modality == modality), 4)[[1]]
  
  srs <- trials2counts(stimID = df$stimuli, response = df$reponse,rating = df$Confidence_bin,nRatings = 4)
  
  conf <- plot_conf(srs)
  
  f <- data.frame(Confidence_bin = 1:4, correct = conf[[1]], incorrect = conf[[2]]) %>% 
    pivot_longer(cols = c("correct", "incorrect"), names_to = "ResponseCorrect", values_to = "procent")
  
  f$Modality <- modality
  
  return(f)
}


# plotting the histogram of the confidence ratings.
plot_confidence <- function(df, n_mod) {
  if (n_mod == 2) {
    f <- rbind(get_df(df, "Extero"), get_df(df, "Intero"))
  } else {
    modality <- as.character(unique(df$Modality))
    f <- get_df(df, modality)
  }
  
  f$Modality <- as.factor(f$Modality)
  
  plot <- f %>%
    mutate() %>%
    ggplot(aes(fill = ResponseCorrect)) +
    geom_col(aes(x = Confidence_bin, y = procent), position = "dodge", col = "black") +
    scale_fill_manual(values = c("#5f9e6e", "#b55d60")) +
    theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(), panel.background = element_blank(), axis.line = element_line(colour = "black"), plot.title = element_text(hjust = 0.5)) +
    scale_color_manual(values = "black") +
    guides(color = "none") +
    facet_wrap(~Modality, scales = "free_y") +
    ylab("P(Confidence = y|Outcome)") +
    xlab(" ")
  
  return(plot)
}






# histogram plot of the intensities in the modalities.
intensity_plot <- function(df) {
  # plotting Intensity as a fucntion of Modality
  
  intensityplot <- df %>%
    ggplot(aes(x = Alpha)) +
    geom_histogram(aes(y = ..density.., col = "black", fill = Modality), position = "identity", alpha = 0.6, binwidth = 6.65) +
    ggtitle(label = "Distribution of the tested intensities values") +
    xlab(label = "Intensity (BPM)") +
    scale_fill_manual(values = if (length(unique(df$Modality)) < 2 && unique(df$Modality) == "Intero") {
      c("#c44e52")
    } else if (length(unique(df$Modality)) < 2 && unique(df$Modality) == "Extero") {
      c("#4c72b0")
    } else {
      c("#4c72b0", "#c44e52")
    }) +
    scale_x_continuous(breaks = seq(-40, 40, by = 10)) +
    ylab(label = "") +
    scale_y_continuous(breaks = seq(0, 0.06, by = 0.01)) +
    theme(
      panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
      panel.background = element_blank(), axis.line = element_line(colour = "black"), plot.title = element_text(hjust = 0.5)
    ) +
    scale_color_manual(values = "black") +
    guides(color = "none")
  return(intensityplot)
}


# function to get confidence intervals used in plot_intervals.
ci <- function(x) {
  list <- list(
    which(cumsum(x) / sum(x) > 0.025)[1],
    last(which(cumsum(x) / sum(x) < 0.975))
  )
  return(list)
}

# function to get the line intervals from the exteropost and interopost dataframe
get_line_intervals <- function(data, Modality) {
  if (Modality == "Extero") {
    color <- "blue"
  }
  if (Modality == "Intero") {
    color <- "red"
  }
  
  
  upper <- array(NA, np$size(data[, 1, 1]))
  lower <- array(NA, np$size(data[, 1, 1]))
  
  for (i in 1:np$size(data[, 1, 1])) {
    confidence <- ci(rowMeans(data, dims = 2)[i, ])
    rg <- seq(-50.5, 50.5, by = 1)
    upper[i] <- rg[confidence[[1]]]
    lower[i] <- rg[confidence[[2]]]
  }
  
  data <- data.frame(upper = upper, lower = lower, col = color, Modality = Modality, x = seq(0, nrow(upper), length.out = nrow(upper)))
  
  return(data)
}



plot_interval <- function(df, exteroPost = NA, interoPost = NA) {
  d <- data.frame()
  dd <- data.frame()
  
  # the confidence intervals for the plot extracted here
  if (!is.na(exteroPost)[1] == TRUE) {
    d <- get_line_intervals(exteroPost, "Extero")
  }
  if (!is.na(interoPost)[1] == TRUE) {
    dd <- get_line_intervals(interoPost, "Intero")
  }
  d <- rbind(d, dd)
  
  # The different colours for the points and lines:
  df$col <- ifelse(df$Modality == "Extero" & df$TrialType == "psi", df$col <- "blue", ifelse(df$Modality == "Intero" & df$TrialType == "psi", df$col <- "red", df$col <- "grey"))
  
  # the Line in the plot:
  dataline1 <- df %>%
    filter(TrialType == "psi") %>%
    filter(Modality == "Extero") %>%
    mutate(x = seq(0, nrow(.), length.out = (nrow(.))))
  dataline2 <- df %>%
    filter(TrialType == "psi") %>%
    filter(Modality == "Intero") %>%
    mutate(x = seq(0, nrow(.), length.out = (nrow(.))))
  dataline <- rbind(dataline1, dataline2)
  
  # making trials go from 0-60 in each Modality
  df <- df %>%
    group_by(Modality) %>%
    mutate(trials = 1:n()) %>%
    ungroup()
  # plot
  
  if (length(unique(df$Modality)) == 2) {
    intervalplot <- df %>% ggplot(aes()) +
      geom_point(aes(x = trials, y = Alpha, color = col, shape = Decision), size = 2.5) +
      # shapes' shape
      scale_shape_manual(values = c(0, 16)) +
      scale_color_manual(values = c("#4c72b0", "black", "#c44e52")) +
      # 0 line
      geom_hline(yintercept = 0, linetype = "dashed", alpha = 0.5) +
      # line that is inside Confidence interval
      geom_line(data = dataline, aes(x = x, y = EstimatedThreshold, color = col)) +
      # confidence interval
      geom_ribbon(data = d, aes(x = x, ymin = lower, ymax = upper, fill = col, alpha = 0.2)) +
      scale_fill_manual("Modality", values = c("#4c72b0", "#c44e52"), labels = c("Extero", "Intero")) +
      facet_wrap(~Modality, nrow = 2, scale = "free") +
      # themes and text
      guides(color = "none", alpha = "none") +
      scale_x_continuous(name = "Trials", limits = c(0, nrow(df) / 2), breaks = seq(0, nrow(df) / 2, by = 10)) +
      scale_y_continuous(name = expression(paste("Intensity  (", Delta, "BPM)"))) +
      theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(), panel.background = element_blank(), axis.line = element_line(colour = "black"))
  }
  
  if (length(unique(df$Modality)) == 1) {
    if (unique(as.character(df$Modality == "Intero"))) {
      intervalplot <- df %>% ggplot(aes()) +
        geom_point(aes(x = trials, y = Alpha, color = col, shape = Decision), size = 2.5) +
        # shapes' shape
        scale_shape_manual(values = c(0, 16)) +
        scale_color_manual(values = c("#c44e52", "black")) +
        # 0 line
        geom_hline(yintercept = 0, linetype = "dashed", alpha = 0.5) +
        # line that is inside Confidence interval
        geom_line(data = dataline, aes(x = x, y = EstimatedThreshold, color = col)) +
        # confidence interval
        geom_ribbon(data = d, aes(x = x, ymin = lower, ymax = upper, fill = col, alpha = 0.2)) +
        scale_fill_manual("Modality", values = c("#c44e52"), labels = c("Intero")) +
        # themes and text
        guides(color = "none", alpha = "none") +
        scale_x_continuous(name = "Trials", limits = c(0, nrow(df)), breaks = seq(0, nrow(df), by = 10)) +
        scale_y_continuous(name = expression(paste("Intensity  (", Delta, "BPM)"))) +
        theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(), panel.background = element_blank(), axis.line = element_line(colour = "black"))
    } else {
      intervalplot <- df %>% ggplot(aes()) +
        geom_point(aes(x = trials, y = Alpha, color = col, shape = Decision), size = 2.5) +
        # shapes' shape
        scale_shape_manual(values = c(0, 16)) +
        scale_color_manual(values = c("#4c72b0", "black")) +
        # 0 line
        geom_hline(yintercept = 0, linetype = "dashed", alpha = 0.5) +
        # line that is inside Confidence interval
        geom_line(data = dataline, aes(x = x, y = EstimatedThreshold, color = col)) +
        # confidence interval
        geom_ribbon(data = d, aes(x = x, ymin = lower, ymax = upper, fill = col, alpha = 0.2)) +
        scale_fill_manual("Modality", values = c("#4c72b0"), labels = c("Extero")) +
        # themes and text
        guides(color = "none", alpha = "none") +
        scale_x_continuous(name = "Trials", limits = c(0, nrow(df)), breaks = seq(0, nrow(df), by = 10)) +
        scale_y_continuous(name = expression(paste("Intensity  (", Delta, "BPM)"))) +
        theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(), panel.background = element_blank(), axis.line = element_line(colour = "black"))
    }
  }
  
  return(intervalplot)
}


# plot of the intensitiy vs the probability of answering "more".
analysis_plot <- function(df) {
  # getting the estimatedthreshhold and estimated slope for each modality in the PSI triaLS
  df <- df %>%
    filter(Decision != "NA") %>%
    group_by(Modality) %>%
    summarize(means = last(na.omit(EstimatedThreshold)), sds = last(na.omit(EstimatedSlope))) %>%
    inner_join(df, by = "Modality") %>%
    ungroup()
  
  # making the curves for each modality based on the cumulative normal distribution
  dfq <- df %>%
    filter(Modality == "Extero") %>%
    mutate(x = seq(-40, 40, length.out = nrow(.)), y = pnorm(x, means, sds)) %>%
    ungroup()
  dfqq <- df %>%
    filter(Modality == "Intero") %>%
    mutate(x = seq(-40, 40, length.out = nrow(.)), y = pnorm(x, means, sds)) %>%
    ungroup()
  df <- rbind(dfq, dfqq)
  
  
  # making two data frames one that counts the number of responses in each intensity and morality and one that gives all possible combination of these
  d1 <- df %>%
    filter(Decision != "NA", Decision == "More") %>%
    group_by(Alpha, Modality, Decision) %>%
    summarize(resp = n())
  d2 <- df %>%
    filter(Decision != "NA", Decision == "More") %>%
    tidyr::expand(Modality, Alpha)
  # merging these two where we replace values that are not in the first dataframe (NA's) with 0's as group_by %>% summarize omits these vales from the dataframe
  f1 <- full_join(d1, d2) %>%
    replace_na(list(resp = 0))
  # same is then done for all responses (not only where the response was "more")
  d3 <- df %>%
    filter(Decision != "NA") %>%
    group_by(Alpha, Modality) %>%
    summarize(total = n())
  d4 <- df %>%
    filter(Decision != "NA") %>%
    tidyr::expand(Modality, Alpha)
  f2 <- full_join(d3, d4) %>%
    replace_na(list(total = 0))
  # combing these two then gives a dataframe with both the total amount of answers and the amount of answers that was "more" the procent is then calculated.
  f <- full_join(f1, f2) %>%
    replace_na(list(resp = 0)) %>%
    mutate(procent = resp / total, Decision = "More")
  
  
  # going from sd of normal distribution to slop on cumulative normal in the mean is just differentiating the cumulative normal:
  # that is the normal distribution and you then want to slope at where the mean is which reduces to slope = 1/(sigma*2*pi)
  
  
  
  data1 <- df %>% filter(Modality == "Extero")
  data2 <- df %>% filter(Modality == "Intero")
  
  
  # plot
  analysisplot <- df %>%
    ggplot(aes()) +
    # lines that go from 0.5 on each graph to the Intensity
    geom_segment(aes(x = means, xend = means, y = 0, yend = 0.5, col = Modality), show.legend = FALSE) +
    # points at 0.5
    geom_point(aes(x = means, y = 0.5, col = Modality), size = max(f$total, 4), show.legend = FALSE) +
    # the functions
    geom_line(aes(x = x, y = y, col = Modality), linetype = "dashed") +
    geom_text(data = data1, aes(x = -20, y = 0.75, label = paste("Threshold for ", unique(Modality), "is", round(unique(means), 2)), col = Modality), show.legend = F, stat = "unique") +
    geom_text(data = data1, aes(x = -20, y = 0.70, label = paste("Slope for ", unique(Modality), "is", round((unique(sds)), 2)), col = Modality), show.legend = F, stat = "unique") +
    geom_text(data = data2, aes(x = -20, y = 0.65, label = paste("Threshold for ", unique(Modality), "is", round(unique(means), 2)), col = Modality), show.legend = F, stat = "unique") +
    geom_text(data = data2, aes(x = -20, y = 0.60, label = paste("Slope for ", unique(Modality), "is", round((unique(sds)), 2)), col = Modality), show.legend = F, stat = "unique") +
    # the points
    geom_point(data = f, aes(x = Alpha, y = procent, alpha = 0.5, col = Modality), size = f$total * 5, show.legend = FALSE) +
    # cosmetics
    coord_cartesian(xlim = c(-40, 40)) +
    scale_size(range = c(0, 25)) +
    scale_color_manual(values = if (length(unique(df$Modality)) < 2 && unique(df$Modality) == "Intero") {
      c("#c44e52")
    } else if (length(unique(df$Modality)) < 2 && unique(df$Modality) == "Extero") {
      c("#4c72b0")
    } else {
      c("#4c72b0", "#c44e52")
    }) +
    theme(legend.title = element_blank()) +
    ylab(label = "P(Response = More | Intensity)") +
    xlab(expression(paste("Intensity  (", Delta, "BPM)"))) +
    theme(
      panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
      panel.background = element_blank(), axis.line = element_line(colour = "black"), legend.position = c(0.1, 0.90), legend.key.size = unit(1.5, "cm"), legend.key = element_rect(fill = "white")
    )
  
  df <- data.frame(
    condition = c(unique(data1$Modality), unique(data2$Modality)),
    threshold = c(unique(data1$means), unique(data2$means)),
    slopes = c((unique(data1$sds)), (unique(data2$sds)))
  )
  
  return(list(analysisplot, df))
}


# function to get mean accuracy
get_mean_acc <- function(df) {
  results <- df %>%
    group_by(Modality) %>%
    summarize(mean_confidence = mean(Confidence, na.rm = T)) %>%
    rename(condition = Modality)
  correct <- df %>%
    group_by(Modality, ResponseCorrect) %>%
    summarize(n = as.numeric(n())) %>%
    filter(ResponseCorrect == 1) %>%
    rename(condition = Modality)
  total <- df %>%
    group_by(Modality) %>%
    summarize(n = n())
  correct[1, 3] <- correct[1, 3] / total[1, 2]
  correct[2, 3] <- correct[2, 3] / total[2, 2]
  
  correct$Accuracy <- correct$n
  correct$n <- NULL
  correct$ResponseCorrect <- NULL
  df1 <- inner_join(correct, results)
  
  return(df1)
}







get_AUC = function(df,bins, flem){
  
  get_data = function(df, modality,bins){
    
    if(bins == T){
      m1 = glm(ResponseCorrect ~ Confidence_bin, data = df %>% filter(Modality == modality), family = binomial(link = "logit"))  
    }else{
      m1 = glm(ResponseCorrect ~ Confidence, data = df %>% filter(Modality == modality), family = binomial(link = "logit"))  
      
    }
    roc_con = pROC::roc(df %>% filter(Modality == modality) %>% .$ResponseCorrect , m1$fitted)
    
    auc = pROC::auc(roc_con)
    
    return(pROC::ggroc(roc_con)$data %>% mutate(Modality = modality, AUC = auc[[1]]))
  }
  
  get_AUROC = function(df, modality,bins){
    
    df <- df %>%
      filter(Modality == modality) %>% 
      mutate(stimuli = as.numeric(Alpha > 0), Modality = as.factor(Modality), reponse = as.factor(as.numeric((Decision == "More")))) %>%
      ungroup()
    
    df$Confidence_bin <- discretebins(df, 4)[[1]]
    
    
    model = get_data(df,modality, bins)
    
    return(list(model = model,data = df))
  }
  
  n_mod = length(unique(df$Modality))
  
  if(n_mod == 2){
    int = get_AUROC(df, "Intero",bins)
    ext = get_AUROC(df, "Extero",bins)
    model = rbind(int$model,ext$model)
    
    flem_AUC_I = flemmings(df, "Intero")
    flem_AUC_E = flemmings(df, "Extero")
    
    data = rbind(int$data,ext$data)
    
    names = model %>% group_by(Modality)  %>% slice(1) %>% mutate(AUC = round(AUC,3))
  }else{
    int = get_AUROC(df, unique(df$Modality),bins)
    
    model = rbind(int$model)
    
    data = rbind(int$data)
    
    names = model  %>% slice(1) %>% 
      mutate(AUC = round(AUC,3))
    
  }
  
  AUCplot = model %>% 
    ggplot(aes(col = Modality, group = Modality))+
    geom_line(aes(x=1-specificity, y = sensitivity))+
    theme_classic()+
    geom_text(data = names, aes(x = 0.5,y = 0.2, label = paste0("AUC = ",AUC)),check_overlap = TRUE,position = position_dodge(width = 1))+
    {if(length(unique(df$Modality)) == 1 & unique(df$Modality)[1] == "Intero")scale_color_manual(values = "#c44e52")}+
    {if(length(unique(df$Modality)) == 1 & unique(df$Modality)[1] == "Extero")scale_color_manual(values = "#4c72b0")}+
    {if(length(unique(df$Modality)) == 2)scale_color_manual(values = c("#4c72b0","#c44e52"))}
  
  
  conf_bins = data %>% group_by(Modality, Confidence_bin) %>% summarize(last = last(Confidence))
  
  pointsplot = df %>% 
    ggplot()+
    geom_jitter(aes(y = Confidence, x = as.factor(ResponseCorrect),col = Modality), width = 0.2)+
    theme_classic()+xlab("Correct response")+
    geom_hline(data = conf_bins, aes(yintercept = last, col = Modality))+
    {if(length(unique(df$Modality)) == 1 & unique(df$Modality)[1] == "Intero")scale_color_manual(values = "#c44e52")}+
    {if(length(unique(df$Modality)) == 1 & unique(df$Modality)[1] == "Extero")scale_color_manual(values = "#4c72b0")}+
    {if(length(unique(df$Modality)) == 2)scale_color_manual(values = c("#4c72b0","#c44e52"))}
  
  pointsplot+AUCplot
  
  if(flem == FALSE){
    data = names %>% 
      dplyr::select(Modality, AUC) %>% 
      rename(condition = Modality)
  }
  if(flem == TRUE & n_mod == 2){
    data = names %>% 
      dplyr::select(Modality) %>% 
      rename(condition = Modality) %>% cbind(flem_AUC = c(flem_AUC_I,flem_AUC_E))
  }else if(flem == TRUE & n_mod == 1){
    data = names %>% 
      dplyr::select(Modality, AUC) %>% 
      rename(condition = Modality)
  }
  
  
  
  return(list(plot = AUCplot,data = data))
  
}


flemmings = function(df, modality){
  
  df = df %>% filter(Modality == modality)
  correct = df$ResponseCorrect
  df$Confidence_bin <- discretebins(df, 4)[[1]]
  conf = df$Confidence_bin
  
  Nratings = 4
  
  i <- Nratings + 1
  H2 <- numeric(Nratings)
  FA2 <- numeric(Nratings)
  
  for (c in 1:Nratings) {
    H2[i-1] <- sum(conf == c & correct) + 0.5
    FA2[i-1] <- sum(conf == c & !correct) + 0.5
    i <- i - 1
  }
  
  H2 <- H2 / sum(H2)
  FA2 <- FA2 / sum(FA2)
  cum_H2 <- c(0, cumsum(H2))
  cum_FA2 <- c(0, cumsum(FA2))
  
  i <- 1
  k <- numeric(Nratings)
  
  for (c in 1:Nratings) {
    k[i] <- (cum_H2[c + 1] - cum_FA2[c])^2 - (cum_H2[c] - cum_FA2[c + 1])^2
    i <- i + 1
  }
  
  auroc2 <- 0.5 + 0.25 * sum(k)
  
  # AUROC is stored in 'auroc2'
  return(auroc2)
  
}





#bayesian stuff:


run_bayes_analysis = function(df, model){
  
  # compiling the Stan model:
  mod <- model
  
  results = list()
  i = 0
  for(modality in unique(df$Modality)){
    i = i+1
    
    df_1 <- df %>% 
      filter(Modality == modality) %>% 
      group_by(Alpha) %>%
      summarize(x=mean(Alpha),
                resp = sum(Decision=="More"),
                n = n())
    
    
    standata <- list(N = nrow(df_1), n = df_1$n, y = df_1$resp, x = df_1$Alpha)
    
    if(grepl("Lapse",mod$stan_file())){
      
       fitted = run_lapse(standata,modality,mod)
       
    }else{
      
      fitted = run_normal(standata,modality,mod)
      
    }
    
    results[[modality]] = fitted
  }
  
  
  
  return(results)
  
  
}


run_normal = function(standata,modality,mod){
  

  # running the model:
  fit <- mod$sample(
    data = standata,
    chains = 4,
    parallel_chains = 4,
    refresh = 0,
    iter_warmup = 2000,
    iter_sampling = 2000
  )
  
  if (modality == "Extero") {
    color_scheme_set("blue")
    col <- "#4c72b0"
  } else if(modality == "Intero"){
    color_scheme_set("red")
    col <- "#c44e52"
    
  }else{
    color_scheme_set("grey")
  }
  
  # diagnostics
  chainplot <- bayesplot::mcmc_dens_chains(fit$draws(c("alpha", "beta_unconstrained")))+theme_classic()
  traceplot <- bayesplot::mcmc_trace(fit$draws(c("alpha", "beta_unconstrained")))+theme_classic()
  
  
  data = data.frame(standata) %>% mutate(procent = y/n)
  

  
  datap <- posterior::as_draws_df(fit)
  datamean1 <- datap %>% summarize(alpha = mean(alpha), beta = mean(beta))
  
  datamean <- data.frame(x = seq(-40, 40, by = 1), y = pnorm(seq(-40, 40, by = 1), datamean1$alpha, datamean1$beta))
  
  x <- seq(-40, 40, by = 0.1)
  y1 <- as.data.frame(1:801)
  x1 <- as.data.frame(1:801)
  i1 <- as.data.frame(1:801)
  
  for (i in 1:100) {
    y1[, i] <- pnorm(x, mean = datap$alpha[i], sd = datap$beta[i])
    x1[, i] <- x
    i1[, i] <- rep(i, 801)
  }
  qp <- data.frame(c(ys = pivot_longer(y1, cols = everything()),
                     xs = pivot_longer(x1, cols = everything()),
                     is = pivot_longer(i1, cols = everything())))
  
  
  
  
  bayseplot <- qp %>% ggplot() +
    geom_line(data = qp, aes(x = xs.value, y = ys.value, group = as.factor(is.value)), alpha = 1 / 20, color = "black") +
    geom_line(data = datamean, aes(x = x, y = y), color = col, size = 1.2) +
    geom_point(data = data, aes(x = x, y = procent, size = n * 5, alpha = 0.5, color = col), show.legend = FALSE) +
    coord_cartesian(xlim = c(-35, 35)) +
    scale_size(range = c(0, 15)) +
    geom_text(data = datamean1, aes(x = -25, y = 0.80, label = paste("Threshold for ", modality, "is", round(fit$summary("alpha")$mean, 2), "\u00B1", round(fit$summary("alpha")$sd, 2)), col = col), size = 3, show.legend = F) +
    geom_text(data = datamean1, aes(x = -25, y = 0.70, label = paste("Slope for ", modality, "is", round(fit$summary("beta")$mean, 2), "\u00B1", round(fit$summary("beta")$sd, 2)), col = col), size = 3, show.legend = F) +
    scale_color_manual(values = col) +
    theme(legend.title = element_blank()) +
    ylab(label = "P(Response = More | Intensity)") +
    xlab(expression(paste("Intensity  (", Delta, "BPM)"))) +
    theme(
      panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
      panel.background = element_blank(), axis.line = element_line(colour = "black")
    ) +
    scale_x_continuous(breaks = seq(-30, 30, by = 10))
  
  stats <- data.frame(bayesian_alpha_mean = fit$summary("alpha")$mean,
                      bayesian_beta_mean = fit$summary("beta")$mean,
                      bayesian_lambda_mean = NA,
                      bayesian_alpha_sd = fit$summary("alpha")$sd,
                      bayesian_beta_sd = fit$summary("beta")$sd,
                      bayesian_lambda_sd = NA,
                      divergences = mean(fit$diagnostic_summary()$num_divergent),
                      rhat = mean(fit$summary() %>% .$rhat),
                      condition = modality)
  
  
  
  return(list(chainplot = chainplot,traceplot = traceplot,bayseplot = bayseplot, stats = stats))
  
}


run_lapse = function(standata,modality,mod){
  # running the model:
  fit <- mod$sample(
    data = standata,
    chains = 4,
    parallel_chains = 4,
    refresh = 0,
    iter_warmup = 2000,
    iter_sampling = 2000
  )
  
  if (modality == "Extero") {
    color_scheme_set("blue")
    col <- "#4c72b0"
  } else if(modality == "Intero"){
    color_scheme_set("red")
    col <- "#c44e52"
    
  }else{
    color_scheme_set("grey")
  }
  
  # diagnostics
  chainplot <- bayesplot::mcmc_dens_chains(fit$draws(c("alpha", "beta_unconstrained","lambda_unconstrained")))+theme_classic()
  traceplot <- bayesplot::mcmc_trace(fit$draws(c("alpha", "beta_unconstrained","lambda_unconstrained")))+theme_classic()
  
  
  data = data.frame(standata) %>% mutate(procent = y/n)
  
  
  datap <- posterior::as_draws_df(fit)
  datamean1 <- datap %>% summarize(alpha = mean(alpha), beta = mean(beta), lambda = mean(lambda))
  
  datamean <- data.frame(x = seq(-40, 40, by = 1), y = psychometric(seq(-40,40, by = 1), datamean1$alpha,datamean1$beta,datamean1$lambda))
  
  x <- seq(-40, 40, by = 0.1)
  y1 <- as.data.frame(1:801)
  x1 <- as.data.frame(1:801)
  i1 <- as.data.frame(1:801)
  
  for (i in 1:100) {
    y1[, i] <- psychometric(x, datap$alpha[i], datap$beta[i], datap$lambda[i])
    x1[, i] <- x
    i1[, i] <- rep(i, 801)
  }
  qp <- data.frame(c(ys = pivot_longer(y1, cols = everything()),
                     xs = pivot_longer(x1, cols = everything()),
                     is = pivot_longer(i1, cols = everything())))
  
  
  
  
  bayseplot <- qp %>% ggplot() +
    geom_line(data = qp, aes(x = xs.value, y = ys.value, group = as.factor(is.value)), alpha = 1 / 20, color = "black") +
    geom_line(data = datamean, aes(x = x, y = y), color = col, size = 1.2) +
    geom_point(data = data, aes(x = x, y = procent, size = n * 5, alpha = 0.5, color = col), show.legend = FALSE) +
    coord_cartesian(xlim = c(-35, 35)) +
    scale_size(range = c(0, 15)) +
    geom_text(data = datamean1, aes(x = -25, y = 0.80, label = paste("Threshold for ", modality, "is", round(fit$summary("alpha")$mean, 2), "\u00B1", round(fit$summary("alpha")$sd, 2)), col = col), size = 3, show.legend = F) +
    geom_text(data = datamean1, aes(x = -25, y = 0.70, label = paste("Slope for ", modality, "is", round(fit$summary("beta")$mean, 2), "\u00B1", round(fit$summary("beta")$sd, 2)), col = col), size = 3, show.legend = F) +
    scale_color_manual(values = col) +
    theme(legend.title = element_blank()) +
    ylab(label = "P(Response = More | Intensity)") +
    xlab(expression(paste("Intensity  (", Delta, "BPM)"))) +
    theme(
      panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
      panel.background = element_blank(), axis.line = element_line(colour = "black")
    ) +
    scale_x_continuous(breaks = seq(-30, 30, by = 10))
  
  
  
  stats <- data.frame(bayesian_alpha_mean = fit$summary("alpha")$mean,
                      bayesian_beta_mean = fit$summary("beta")$mean,
                      bayesian_lambda_mean = fit$summary("lambda")$mean,
                      bayesian_alpha_sd = fit$summary("alpha")$sd,
                      bayesian_beta_sd = fit$summary("beta")$sd,
                      bayesian_lambda_sd = fit$summary("lambda")$sd,
                      divergences = mean(fit$diagnostic_summary()$num_divergent),
                      rhat = mean(fit$summary() %>% .$rhat),
                      condition = modality)
  
  
  
  return(list(chainplot = chainplot,traceplot = traceplot,bayseplot = bayseplot, stats = stats))
  
}

psychometric = function(x,alpha,beta,lambda){
  return(lambda + (1 - 2 * lambda) * (0.5+0.5*erf((x-alpha)/(beta*sqrt(2)))))
}


psychometric_nolapse = function(x,alpha,beta){
  return((0.5+0.5*erf((x-alpha)/(beta*sqrt(2)))))
}



transform_data_to_stan = function(data){
  
  data = data %>% group_by(Alpha,participant_id, sessions)%>%
    summarise(Alpha=mean(Alpha),
              npx=n(),
              resp=sum(resp))%>%
    ungroup()
  
  return(data)
}

