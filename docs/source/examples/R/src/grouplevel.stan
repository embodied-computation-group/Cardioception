data {
  int<lower=0> ns;
  int<lower=0> ntrial;
  int<lower=0> N[ns];
  int n[ntrial];
  int y[ntrial];
  real x[ntrial];
}
parameters {
  real alpha[ns];
  real<lower=0> beta[ns];
  real mualpha;
  real<lower=0> sigmaalpha;
  real <lower =0> mubeta;
  real<lower=0> sigmabeta;
}

model {
  for (p in 1:ns)
  if (p == 1)
      for (i in 1:N[p])
      y[i] ~ binomial(n[i], 0.5+0.5*erf((x[i]-alpha[p])/(beta[p]*sqrt(2))));
  else
    for (i in N[p-1]:N[p])
      y[i] ~ binomial(n[i], 0.5+0.5*erf((x[i]-alpha[p])/(beta[p]*sqrt(2))));
      
  alpha ~ normal(mualpha,sigmaalpha);
  beta ~ normal(mubeta, sigmabeta);
  mualpha ~ uniform(-50,50);
  sigmaalpha ~ normal(0,10);
  mubeta ~ uniform(0,10);
  sigmabeta ~ normal(0,10);

}

