data {
  int<lower=0> N;
  int<lower=0> n[N];
  int y[N];
  vector[N] x;
}
parameters {
  real alpha;
  real<lower=0> beta;
}

model {
  for (i in 1:N)
    y[i] ~ binomial(n[i], 0.5+0.5*erf((x[i]-alpha)/(beta*sqrt(2))));
    
  alpha ~ uniform(-40.5,40.5);
  beta ~ normal(0,10);
    
}
