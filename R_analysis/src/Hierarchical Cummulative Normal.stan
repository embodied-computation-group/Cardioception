data{

  //Constants
  int<lower=1> T; // Total number of trials in the data
  int<lower=1> S; // Total number of subjects in the data
  array[T] int S_id; //n vector of integeres that signify participant numbers
  
  int<lower=1> N_alpha; // Number of regressors on the threshold
  int<lower=1> N_beta; // Number of regressors on the slope
  int<lower=1> N_lapse; // Number of regressors on the lapserate
  

  matrix[T,N_alpha] X_alpha; // Design matrix for the threshold
  matrix[T,N_beta] X_beta; // Design matrix for the slope 
  matrix[T,N_lapse] X_lapse; // Design matrix for the lapserate

  
  array[T] int Y; // Vector of binary responses
  array[T] int npx; // Vector of binary responses

  vector[T] X; // Vector of deltaBPM values that match the binary response

  

}
transformed data{
  int<lower=1> N=N_alpha+N_beta+N_lapse; //Number of free parameters

}
parameters{
  
  vector[N] gm;  // Group means 

  vector<lower = 0>[N]  tau_u;   // Between participant scales

  cholesky_factor_corr[N] L_u;    // Between participant cholesky decomposition

  matrix[N, S] z_expo;    // Participant deviation from the group means

}
transformed parameters{
  ///Recomposition of parameters (i.e. calculating the linear combination of parameters and design matrix.)
  
  vector[T] alpha;
  vector<lower=0>[T] beta;
  vector<lower=0, upper = 0.5>[T] lapse;


  // Extracting individual deviations for each subject for each parameter
  matrix[S, N] indi_dif = (diag_pre_multiply(tau_u, L_u) * z_expo)';
  
  matrix[S, N] param;
  
  // adding the participant deviation to the group means
  for(n in 1:N){
    param[,n]= gm[n] + indi_dif[,n];
  }
  
  // Extracting the parameters for each of the 3 parameters of the psychometric for each subject:
  
  matrix[S,N_beta] beta_p = param[,1:N_beta];
  
  matrix[S,N_lapse] lapse_p = param[,(N_beta+1):(N_lapse+N_beta)];
  
  matrix[S,N_alpha] alpha_p = param[,(N_lapse+N_beta+1):N];

  // Trial loop getting trial by trial threshold slope and lapserate.
  
  for(n in 1:T){

    alpha[n] = dot_product(X_alpha[n,], alpha_p[S_id[n],]);
    
    beta[n] = exp(dot_product(X_beta[n,], beta_p[S_id[n],]));
    
    lapse[n] = inv_logit(dot_product(X_lapse[n,], lapse_p[S_id[n],])) / 2;
    
    }
    
}

model{
  // Defining priors.

  gm[1] ~ normal(2.25,0.5); //global mean of beta
  
  gm[2] ~ normal(0, 3); //global mean of beta
  
  gm[3] ~ normal(-5.5,1.5); //global mean of lapse

  gm[4] ~ normal(-10,10); //global mean of alpha

  gm[5] ~ normal(0,10); //global mean of alpha
  

  to_vector(z_expo) ~ std_normal();
  
  tau_u[1] ~ normal(0.25,0.5);
  tau_u[2] ~ normal(0, 3);
  tau_u[3] ~ normal(2.5,1);
  tau_u[4] ~ normal(10, 10);
  tau_u[5] ~ normal(0, 10);
    
  L_u ~ lkj_corr_cholesky(2);
  
  // Computing the likelihood. The cummulative normal is used here:

  Y ~ binomial(npx, lapse + (1 - 2 * lapse) .* ((0.5+0.5 * erf((X-alpha) ./ (beta * sqrt(2))))));
  
}

generated quantities{
  // Calculating the correlation matrix from the cholesky decomposition.
  real centered  = 0;
  matrix[N,N] correlation_matrix = L_u*L_u';

  
}
