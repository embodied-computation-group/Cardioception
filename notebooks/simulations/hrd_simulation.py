import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import norm
from typing import Union, Optional
import pymc as pm
import arviz as az
import aesara.tensor as at
from ipywidgets import widgets
from IPython.display import display


def simulate_hrd(
    mean_hr: float, 
    std_hr: float, 
    mean_belief: Optional[float] = 60.0, 
    std_belief: Optional[float] = 10.0, 
    interoceptive_accuracy: Optional[float] = -7.0,
    interoceptive_precision: Optional[float] = 10.0,
    n_boot: int = 1000,
    agent: Union[str, float] = "interoceptor"
)->pd.DataFrame:
    """Simulate responses from the the Heart Rate Discrimination task.
    
    Parameters
    ----------
    mean_hr : float
        The mean of the inter-trials heart rate variability.
    std_hr : float
        The standard deviation of the inter-trials heart rate variability.
    mean_beliefs : float
        The mean of the simulated participant's beliefs. Only relevant if `agent="believer"`.
    std_belief: float
        The standard deviation of the simulated participant's beliefs. Only relevant if
        `agent="believer"`.
    agent : str | float
        What kind of agent to use to simulate the responses. If `agent="interoceptor"`, the
        agent use the perceived heart rate and compare it to the tone value. If `agent="believer"`,
        the agent only use the tone values, and compare it to the internal cardiac belief to
        generate the responses. If a float value is provided, the participaant use a mix between
        these two strategies, and `agent` is the proportion of interoception (between 0 and 1).
    
    Returns
    -------
    hrd_df : pd.DataFrame
        The data frame containing the simulated trials.
    
    """

    # Sample the inter-trial heart rates - this is the average of the heart rate
    # recorded during the listening phase of the task
    hr = np.random.normal(loc=mean_hr, scale=std_hr, size=(n_boot, 100))

    # Alpha values being tested - The alpha value is the difference between the
    # heart rate recorded and the tone that is presented to the participant
    alphas = np.repeat([np.arange(-50, 50)], n_boot, axis=0)

    # Values of the tones being tested
    tones = hr + alphas

    # Responses provided by the participant - 0 when the response
    # is "lower" and 1 when the response is "Faster"
    if agent == "interoceptor":
        
        # The agent uses both the provided tones and the perceived heart rate with some
        # noise (interoceptive accuracy) to estimate the alphas values, and use
        # these values to produce the responses
        
        # Perceived heart_rate
        cardiac_signal = hr + np.random.normal(
            loc=interoceptive_accuracy, scale=interoceptive_precision,
            size=(n_boot, 100)
        )
        
        responses = (cardiac_signal < tones).astype(int)

    elif agent == "believer":
        
        # The agent compare the tones to the cardiac belief only
        # and produces responses accordingly
        responses = np.random.binomial(
            n=1, p=norm.cdf(tones, loc=mean_belief, scale=std_belief)
        )
    
    elif isinstance(agent, float):
        assert 0.0 <= agent <= 1.0
    
    # Store the variables in a data frame
    hrd_df = pd.DataFrame(
        {
        "heart_rate": hr.flatten(), "alphas": alphas.flatten(),
        "tones": tones.flatten(), "responses": responses.flatten()}
    )

    return hrd_df