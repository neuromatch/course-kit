---
title: "Tutorial 1: Linear Dynamical Systems"
# Keeps the section ids of the original NMA notebook (W2D2 Tutorial 1)
feedback_prefix: W2D2_T1
kernelspec:
  name: python3
  display_name: Python 3
---

```{code-cell} python
# Pyodide compatibility — install packages not bundled by default
import sys
if sys.platform == "emscripten":
    import micropip
    await micropip.install(["ipywidgets"])
```

# Tutorial 1: Linear dynamical systems

**Week 2, Day 3: Linear Systems**

**By Neuromatch Academy**

**Content Creators**: Bing Wen Brunton, Alice Schwarze

**Content Reviewers**: Norma Kuhn, Karolina Stosio, John Butler, Matthew Krause, Ella Batty, Richard Gao, Michael Waskom

**Production editors:** Gagana B, Spiros Chavlis

---
# Tutorial Objectives

*Estimated timing of tutorial: 1 hour*

In this tutorial, we will be learning about behavior of dynamical systems -- systems that evolve in time -- where the rules by which they evolve in time are described precisely by a differential equation.

Differential equations are equations that express the **rate of change** of the state variable $x$. One typically describes this rate of change using the derivative of $x$ with respect to time ($dx/dt$) on the left hand side of the differential equation:

\begin{equation}
\frac{dx}{dt} = f(x)
\end{equation}

A common notational short-hand is to write $\dot{x}$ for $\frac{dx}{dt}$. The dot means "the derivative with respect to time".

Today, the focus will be on **linear dynamics**, where $f(x)$ is a linear function of $x$. In Tutorial 1, we will:

* Explore and understand the behavior of such systems where $x$ is a single variable
* Consider cases where $\mathbf{x}$ is a state vector representing two variables.

:::{nma-slides} snv4m
:::

---
# Setup

```{code-cell} python
# Imports
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp  # numerical integration solver
```

```{code-cell} python
:tags: [hide-input]
# @title Figure settings
import logging
logging.getLogger('matplotlib.font_manager').disabled = True

import ipywidgets as widgets  # interactive display
%config InlineBackend.figure_format = 'retina'
_nma_style = "https://raw.githubusercontent.com/NeuromatchAcademy/course-content/main/nma.mplstyle"
if sys.platform == "emscripten":
  # Pyodide has no sockets, so matplotlib can't download the style itself.
  # Fetch it through the browser and load it from a local file.
  from pyodide.http import open_url
  with open("nma.mplstyle", "w") as f:
    f.write(open_url(_nma_style).read())
  _nma_style = "nma.mplstyle"
plt.style.use(_nma_style)
```

```{code-cell} python
:tags: [hide-input]
# @title Plotting Functions
def plot_trajectory(system, params, initial_condition, dt=0.1, T=6,
                    figtitle=None):

  """
  Shows the solution of a linear system with two variables in 3 plots.
  The first plot shows x1 over time. The second plot shows x2 over time.
  The third plot shows x1 and x2 in a phase portrait.

  Args:
    system (function): a function f(x) that computes a derivative from
                        inputs (t, [x1, x2], *params)
    params (list or tuple): list of parameters for function "system"
    initial_condition (list or array): initial condition x0
    dt (float): time step of simulation
    T (float): end time of simulation
    figtitlte (string): title for the figure

  Returns:
    nothing, but it shows a figure
  """

  # time points for which we want to evaluate solutions
  t = np.arange(0, T, dt)

  # Integrate
  # use built-in ode solver
  solution = solve_ivp(system,
                    t_span=(0, T),
                    y0=initial_condition, t_eval=t,
                    args=(params),
                    dense_output=True)
  x = solution.y

  # make a color map to visualize time
  timecolors = np.array([(1 , 0 , 0, i)  for i in t / t[-1]])

  # make a large figure
  fig, (ah1, ah2, ah3) = plt.subplots(1, 3)
  fig.set_size_inches(10, 3)

  # plot x1 as a function of time
  ah1.scatter(t, x[0,], color=timecolors)
  ah1.set_xlabel('time')
  ah1.set_ylabel('x1', labelpad=-5)

  # plot x2 as a function of time
  ah2.scatter(t, x[1], color=timecolors)
  ah2.set_xlabel('time')
  ah2.set_ylabel('x2', labelpad=-5)

  # plot x1 and x2 in a phase portrait
  ah3.scatter(x[0,], x[1,], color=timecolors)
  ah3.set_xlabel('x1')
  ah3.set_ylabel('x2', labelpad=-5)
  #include initial condition is a blue cross
  ah3.plot(x[0,0], x[1,0], 'bx')

  # adjust spacing between subplots
  plt.subplots_adjust(wspace=0.5)

  # add figure title
  if figtitle is not None:
    fig.suptitle(figtitle, size=16)
  plt.show()


def plot_streamplot(A, ax, figtitle=None, show=True):
  """
  Show a stream plot for a linear ordinary differential equation with
  state vector x=[x1,x2] in axis ax.

  Args:
    A (numpy array): 2x2 matrix specifying the dynamical system
    ax (matplotlib.axes): axis to plot
    figtitle (string): title for the figure
    show (boolean): enable plt.show()

  Returns:
    nothing, but shows a figure
  """

  # sample 20 x 20 grid uniformly to get x1 and x2
  grid = np.arange(-20, 21, 1)
  x1, x2 = np.meshgrid(grid, grid)

  # calculate x1dot and x2dot at each grid point
  x1dot = A[0,0] * x1 + A[0,1] * x2
  x2dot = A[1,0] * x1 + A[1,1] * x2

  # make a colormap
  magnitude = np.sqrt(x1dot ** 2 + x2dot ** 2)
  color = 2 * np.log1p(magnitude) #Avoid taking log of zero

  # plot
  plt.sca(ax)
  plt.streamplot(x1, x2, x1dot, x2dot, color=color,
                 linewidth=1, cmap=plt.cm.cividis,
                 density=2, arrowstyle='->', arrowsize=1.5)
  plt.xlabel(r'$x1$')
  plt.ylabel(r'$x2$')

  # figure title
  if figtitle is not None:
    plt.title(figtitle, size=16)

  # include eigenvectors
  if True:
    # get eigenvalues and eigenvectors of A
    lam, v = np.linalg.eig(A)

    # get eigenvectors of A
    eigenvector1 = v[:,0].real
    eigenvector2 = v[:,1].real

    # plot eigenvectors
    plt.arrow(0, 0, 20*eigenvector1[0], 20*eigenvector1[1],
              width=0.5, color='r', head_width=2,
              length_includes_head=True)
    plt.arrow(0, 0, 20*eigenvector2[0], 20*eigenvector2[1],
              width=0.5, color='b', head_width=2,
              length_includes_head=True)
  if show:
    plt.show()


def plot_specific_example_stream_plots(A_options):
  """
  Show a stream plot for each A in A_options

  Args:
    A (list): a list of numpy arrays (each element is A)

  Returns:
    nothing, but shows a figure
  """
  # get stream plots for the four different systems
  plt.figure(figsize=(10, 10))

  for i, A in enumerate(A_options):

    ax = plt.subplot(2, 2, 1+i)
    # get eigenvalues and eigenvectors
    lam, v = np.linalg.eig(A)

    # plot eigenvalues as title
    # (two spaces looks better than one)
    eigstr = ",  ".join([f"{x:.2f}" for x in lam])
    figtitle =f"A with eigenvalues\n"+ '[' + eigstr + ']'
    plot_streamplot(A, ax, figtitle=figtitle, show=False)

    # Remove y_labels on righthand plots
    if i % 2:
      ax.set_ylabel(None)
    if i < 2:
      ax.set_xlabel(None)

    plt.subplots_adjust(wspace=0.3, hspace=0.3)
  plt.show()
```

---
# Section 1: One-dimensional Differential Equations

:::{nma-video} Video 1: Linear Dynamical Systems
:youtube: 87z6OR7-DBI
:bilibili: BV1up4y1S7wj
:::

:::{nma-feedback} Linear_Dynamical_Systems_Video
:::

This video serves as an introduction to dynamical systems as the mathematics of things that change in time, including examples of relevant timescales relevant for neuroscience. It covers the definition of a linear system and why we are spending a whole day on linear dynamical systems, and walks through solutions to one-dimensional, deterministic dynamical systems, their behaviors, and stability criteria.

Note that this section is a recap of [Tutorials 2](https://compneuro.neuromatch.io/tutorials/W0D4_Calculus/student/W0D4_Tutorial2.html) and [3](https://compneuro.neuromatch.io/tutorials/W0D4_Calculus/student/W0D4_Tutorial3.html) of our pre-course calculus day.

<details>
<summary> <font color='blue'>Click here for text recap of video </font></summary>

Let's start by reminding ourselves of a one-dimensional differential equation in $x$ of the form

$$\dot{x} = a x$$

where $a$ is a scalar.

Solutions for how $x$ evolves in time when its dynamics are governed by such a differential equation take the form

\begin{equation}
x(t) = x_0\exp(a t)
\end{equation}

where $x_0$ is the **initial condition** of the equation -- that is, the value of $x$ at time $0$.
</details>

To gain further intuition, let's explore the behavior of such systems with a simple simulation. We can simulate an ordinary differential equation by approximating or modeling time as a discrete list of time steps $t_0, t_1, t_2, \dots$, such that $t_{i+1}=t_i+dt$. We can get the small change $dx$ over a small duration $dt$ of time from the definition of the differential:

$$
\begin{aligned}
\dot x &= \frac{dx}{dt} \\
dx &= \dot x\, dt
\end{aligned}
$$

So, at each time step $t_i$, we compute a value of $x$, $x(t_i)$, as the sum of the value of $x$ at the previous time step, $x(t_{i-1})$ and a small change $dx=\dot x\,dt$:

\begin{equation}
x(t_i)=x(t_{i-1})+\dot x(t_{i-1}) dt
\end{equation}

This very simple integration scheme, known as **forward Euler integration**, works well if $dt$ is small and the ordinary differential equation is simple. It can run into issues when the ordinary differential equation is very noisy or when the dynamics include sudden big changes of $x$. Such big jumps can occur, for example, in models of excitable neurons. In such cases, one needs to choose an integration scheme carefully. However, for our simple system, the simple integration scheme should work just fine!

## Coding Exercise 1: Forward Euler Integration

*Referred to as Exercise 1B in video*

In this exercise, we will complete a function, ``integrate_exponential``, to compute the solution of the differential equation $\dot{x} = a x$ using forward Euler integration. We will then plot this solution over time.

```{code-cell} python
def integrate_exponential(a, x0, dt, T):
  """Compute solution of the differential equation xdot=a*x with
  initial condition x0 for a duration T. Use time step dt for numerical
  solution.

  Args:
    a (scalar): parameter of xdot (xdot=a*x)
    x0 (scalar): initial condition (x at time 0)
    dt (scalar): timestep of the simulation
    T (scalar): total duration of the simulation

  Returns:
    ndarray, ndarray: `x` for all simulation steps and the time `t` at each step
  """

  # Initialize variables
  t = np.arange(0, T, dt)
  x = np.zeros_like(t, dtype=complex)
  x[0] = x0 # This is x at time t_0

  # Step through system and integrate in time
  for k in range(1, len(t)):

    ###################################################################
    ## Fill out the following then remove
    raise NotImplementedError("Student exercise: need to implement simulation")
    ###################################################################

    # for each point in time, compute xdot from x[k-1]
    xdot = ...

    # Update x based on x[k-1] and xdot
    x[k] = ...

  return x, t


# Choose parameters
a = -0.5    # parameter in f(x)
T = 10      # total Time duration
dt = 0.001  # timestep of our simulation
x0 = 1.     # initial condition of x at time 0

# Use Euler's method
x, t = integrate_exponential(a, x0, dt, T)

# Visualize
plt.plot(t, x.real)
plt.xlabel('Time (s)')
plt.ylabel('x')
plt.show()
```

::::{nma-solution}
```python
def integrate_exponential(a, x0, dt, T):
  """Compute solution of the differential equation xdot=a*x with
  initial condition x0 for a duration T. Use time step dt for numerical
  solution.

  Args:
    a (scalar): parameter of xdot (xdot=a*x)
    x0 (scalar): initial condition (x at time 0)
    dt (scalar): timestep of the simulation
    T (scalar): total duration of the simulation

  Returns:
    ndarray, ndarray: `x` for all simulation steps and the time `t` at each step
  """

  # Initialize variables
  t = np.arange(0, T, dt)
  x = np.zeros_like(t, dtype=complex)
  x[0] = x0 # This is x at time t_0

  # Step through system and integrate in time
  for k in range(1, len(t)):
    # for each point in time, compute xdot from x[k-1]
    xdot = (a*x[k-1])

    # Update x based on x[k-1] and xdot
    x[k] = x[k-1] +  xdot * dt

  return x, t


# Choose parameters
a = -0.5    # parameter in f(x)
T = 10      # total Time duration
dt = 0.001  # timestep of our simulation
x0 = 1.     # initial condition of x at time 0

# Use Euler's method
x, t = integrate_exponential(a, x0, dt, T)

# Visualize
with plt.xkcd():
  plt.plot(t, x.real)
  plt.xlabel('Time (s)')
  plt.ylabel('x')
  plt.show()
```
::::

:::{nma-feedback} Forward_Euler_Integration_Exercise
:::

## Interactive Demo 1: Forward Euler Integration

1.  What happens when you change $a$? Try values where $a<0$ and $a>0$.

2.  The $dt$ is the step size of the forward Euler integration. Try $a = -1.5$ and increase $dt$. What happens to the numerical solution when you increase $dt$?

```{code-cell} python
:tags: [hide-input]
# @markdown Make sure you execute this cell to enable the widget!

T = 10  # total Time duration
x0 = 1.  # initial condition of x at time 0

@widgets.interact(
    a=widgets.FloatSlider(value=-0.5, min=-2.5, max=1.5, step=0.25,
                          description="α", readout_format='.2f'),
    dt=widgets.FloatSlider(value=0.001, min=0.001, max=1.0, step=0.001,
                           description="dt", readout_format='.3f')
    )

def plot_euler_integration(a, dt):
  # Have to do this clunky word around to show small values in slider accurately
  # (from https://github.com/jupyter-widgets/ipywidgets/issues/259)

  x, t = integrate_exponential(a, x0, dt, T)
  plt.plot(t, x.real)  # integrate_exponential returns complex
  plt.xlabel('Time (s)')
  plt.ylabel('x')
  plt.show()
```

:::{nma-explanation}
1. For $a<0$, the solution decays in time.
   For $a>0$, the solution grows in time.
   For $a=0$, the solution stays at 1 (and is stable).

2. For small-ish $dt$, the solution still looks the same.
   As $dt$ gets bigger, the solution starts to look choppier and is no longer smooth,
   but still has mostly the right trends.
   For $a = 0.15$, as $dt$ gets above 0.7 or so, we start to see the forward Euler
   integration starts to actually break down. Specifically, the solution is no
   longer decreasing monotonically and has developed an erroneous dip below zero.

The more general lesson is that, for each system, there is a $dt$ threshold
above which the simulation introduces numerical artifacts and no longer behaves
as an accurate estimate of the true underlying system. We may tolerate some
choppiness in the solution, but eventually qualitatively wrong things creep in!
:::

:::{nma-feedback} What_models_Video
:::

---
# Section 2: Oscillatory Dynamics

*Estimated timing to here from start of tutorial: 20 min*

:::{nma-video} Video 2: Oscillatory Solutions
:youtube: vPYQPI4nKT8
:bilibili: BV1gZ4y1u7PK
:::

:::{nma-feedback} Forward_Euler_Integration_Interactive_Demo_Discussion
:::

We will now explore what happens when $a$ is a complex number and has a non-zero imaginary component.

## Interactive Demo 2: Oscillatory Dynamics

*Referred to as exercise 1B in video*

In the following demo, you can change the real part and imaginary part of $a$ (so a = real + imaginary i)

1. What values of $a$ produce dynamics that both ***oscillate*** and ***grow***?
2. What value of $a$ is needed to produce a stable oscillation of 0.5 Hertz (cycles/time units)?

```{code-cell} python
:tags: [hide-input]
# @markdown Make sure you execute this cell to enable the widget!

# parameters
T = 5  # total Time duration
dt = 0.0001  # timestep of our simulation
x0 = 1.  # initial condition of x at time 0

@widgets.interact
def plot_euler_integration(real=(-2, 2, .2), imaginary=(-4, 7, .1)):

  a = complex(real, imaginary)
  x, t = integrate_exponential(a, x0, dt, T)
  plt.plot(t, x.real)  # integrate exponential returns complex
  plt.grid(True)
  plt.xlabel('Time (s)')
  plt.ylabel('x')
  plt.show()
```

:::{nma-explanation}
1. To make the system both oscillate and grow, `real` has to be positive,
   and `imaginary` has to be non-zero.

2. Stable oscillation of 0.5 Hz (half a cycle per unit time, or one cycle per two
   unit time) is achieved with `real` $= 0$ and `imaginary` $= \pm\pi$
   (approximately 3.1 or -3.1).

Note: For really large values of the imaginary component, the numerical
integration scheme breaks down a bit, and we see non-stable oscillations
even when real=0. This is a numerical artifact of the forward Euler scheme.
Some of the students may discover this if they push the parameters, but I've
tried to constrain the widget so that it is not obvious, as it is not the point
of this exercise.
:::

:::{nma-feedback} Oscillatory_Dynamics_Interactive_Demo_Discussion
:::

---
# Section 3: Deterministic Linear Dynamics in Two Dimensions

*Estimated timing to here from start of tutorial: 33 min*

:::{nma-video} Video 3: Multi-Dimensional Dynamics
:youtube: c_GdNS3YH_M
:bilibili: BV1pf4y1R7uy
:::

:::{nma-feedback} MultiDimensional_Dynamics_Video
:::

This video serves as an introduction to two-dimensional, deterministic dynamical systems written as a vector-matrix equation. It covers stream plots and how to connect phase portraits with the eigenvalues and eigenvectors of the transition matrix A.


<details>
<summary> <font color='blue'>Click here for text recap of relevant part of video </font></summary>

Adding one additional variable (or _dimension_) adds more variety of behaviors. Additional variables are useful in modeling the dynamics of more complex systems with richer behaviors, such as systems of multiple neurons. We can write such a system using two linear ordinary differential equations:

$$
\begin{aligned}
  \dot{x}_1 &= {a}_{11} x_1 \\
  \dot{x}_2 &= {a}_{22} x_2
\end{aligned}
$$

So far, this system consists of two variables (e.g. neurons) in isolation. To make things interesting, we can add interaction terms:

$$
\begin{aligned}
  \dot{x}_1 &= {a}_{11} x_1 + {a}_{12} x_2 \\
  \dot{x}_2 &= {a}_{21} x_1 + {a}_{22} x_2
\end{aligned}
$$

We can write the two equations that describe our system as one (vector-valued) linear ordinary differential equation:

$$\dot{\mathbf{x}} = \mathbf{A} \mathbf{x}$$

For two-dimensional systems, $\mathbf{x}$ is a vector with 2 elements ($x_1$ and $x_2$) and $\mathbf{A}$ is a $2 \times 2$ matrix with $\mathbf{A}=\begin{bmatrix} a_{11} & a_{12} \\ a_{21} & a_{22} \end{bmatrix}$.

</details>

## Coding Exercise 3: Sample trajectories in 2 dimensions

*Referred to in video as step 1 and 2 of exercise 1C*

We want to simulate some **trajectories** of a given system and plot how  $x_1$  and  $x_2$  evolve in time. We will begin with this example system:

\begin{equation}
\dot{\mathbf{x}} = \begin{bmatrix} 2 & -5 \\ 1 & -2 \end{bmatrix} \mathbf{x}
\end{equation}

We will use an integrator from scipy, so we won't have to solve the system ourselves. We have a helper function, ``plot_trajectory``, that plots these trajectories given a system function. In this exercise, we will write the system function for a linear system with two variables.

```{code-cell} python
def system(t, x, a00, a01, a10, a11):
  '''
  Compute the derivative of the state x at time t for a linear
  differential equation with A matrix [[a00, a01], [a10, a11]].

  Args:
    t (float): time
    x (ndarray): state variable
    a00, a01, a10, a11 (float): parameters of the system

  Returns:
    ndarray: derivative xdot of state variable x at time t
  '''
  #################################################
  ## TODO for students: Compute xdot1 and xdot2 ##
  ## Fill out the following then remove
  raise NotImplementedError("Student exercise: say what they should have done")
  #################################################

  # compute x1dot and x2dot
  x1dot = ...
  x2dot = ...

  return np.array([x1dot, x2dot])


# Set parameters
T = 6 # total time duration
dt = 0.1 # timestep of our simulation
A = np.array([[2, -5],
              [1, -2]])
x0 = [-0.1, 0.2]

# Simulate and plot trajectories
plot_trajectory(system, [A[0, 0], A[0, 1], A[1, 0], A[1, 1]], x0, dt=dt, T=T)
```

::::{nma-solution}
```python
def system(t, x, a00, a01, a10, a11):
  '''
  Compute the derivative of the state x at time t for a linear
  differential equation with A matrix [[a00, a01], [a10, a11]].

  Args:
    t (float): time
    x (ndarray): state variable
    a00, a01, a10, a11 (float): parameters of the system

  Returns:
    ndarray: derivative xdot of state variable x at time t
  '''

  # compute x1dot and x2dot
  x1dot = a00 * x[0] + a01 * x[1]
  x2dot = a10 * x[0] + a11 * x[1]

  return np.array([x1dot, x2dot])


# Set parameters
T = 6 # total time duration
dt = 0.1 # timestep of our simulation
A = np.array([[2, -5],
              [1, -2]])
x0 = [-0.1, 0.2]

# Simulate and plot trajectories
with plt.xkcd():
  plot_trajectory(system, [A[0, 0], A[0, 1], A[1, 0], A[1, 1]], x0, dt=dt, T=T)
```
::::

:::{nma-feedback} Sample_trajectories_in_2_dimensions_Exercise
:::

## Interactive Demo 3A: Varying A

We will now use the function we created in the last exercise to plot trajectories with different options for A. What kinds of qualitatively different dynamics do you observe?

**Hint:** Keep an eye on the x-axis and y-axis!

```{code-cell} python
:tags: [hide-input]
# @markdown Make sure you execute this cell to enable the widget!

# parameters
T = 6  # total Time duration
dt = 0.1  # timestep of our simulation
x0 = np.asarray([-0.1, 0.2])  # initial condition of x at time 0

A_option_1 = [[2, -5],[1, -2]]
A_option_2 = [[3,4], [1, 2]]
A_option_3 = [[-1, -1], [0, -0.25]]
A_option_4 = [[3, -2],[2, -2]]

@widgets.interact
def plot_euler_integration(A=widgets.Dropdown(options=[A_option_1,
                                                       A_option_2,
                                                       A_option_3,
                                                       A_option_4,
                                                       None],
                                              value=A_option_1)):
  if A:
    plot_trajectory(system, [A[0][0],A[0][1],A[1][0],A[1][1]], x0, dt=dt, T=T)
```

:::{nma-explanation}
You should observe exponential growth to positive values, exponential
growth to negative values, stable oscillations, and decay to the origin.
:::

:::{nma-feedback} Varying_A_Interactive_Demo_Discussion
:::

## Interactive Demo 3B: Varying Initial Conditions

We will now vary the initial conditions for a given $\mathbf{A}$:

\begin{equation}
\dot{\mathbf{x}} = \begin{bmatrix} 2 & -5 \\ 1 & -2 \end{bmatrix} \mathbf{x}
\end{equation}

What kinds of qualitatively different dynamics do you observe? Hint: Keep an eye on the x-axis and y-axis!

```{code-cell} python
:tags: [hide-input]
# @markdown Make sure you execute this cell to enable the widget!

# parameters
T = 6  # total Time duration
dt = 0.1  # timestep of our simulation
x0 = np.asarray([-0.1, 0.2])  # initial condition of x at time 0
A = [[2, -5],[1, -2]]

x0_option_1 = [-.1, 0.2]
x0_option_2 = [10, 10]
x0_option_3 = [-4, 3]

@widgets.interact
def plot_euler_integration(x0 = widgets.Dropdown(options=[x0_option_1,
                                                          x0_option_2,
                                                          x0_option_3,
                                                          None],
                                                 value=x0_option_1)):
  if x0:
    plot_trajectory(system, [A[0][0], A[0][1], A[1][0], A[1][1]], x0, dt=dt, T=T)
```

:::{nma-explanation}
Changing the initial conditions for this A always produces oscillatory
dynamics. The only difference is the radii of the resulting elliptical
trajectories.
:::

:::{nma-feedback} Varying_Initial_Conditions_Interactive_Demo_Discussion
:::

---
# Section 4: Stream Plots

*Estimated timing to here from start of tutorial: 45 min*

It's a bit tedious to plot trajectories one initial condition at a time!

Fortunately, to get an overview of how a grid of initial conditions affect trajectories of a system, we can use a _stream plot_.

We can think of a initial condition ${\bf x}_0=(x_{1_0},x_{2_0})$  as coordinates for a position in a space. For a 2x2 matrix $\bf A$, a stream plot computes at each position $\bf x$ a small arrow that indicates $\bf Ax$ and then connects the small arrows to form _stream lines_. Remember from the beginning of this tutorial that $\dot {\bf x} = \bf Ax$ is the rate of change of $\bf x$. So the stream lines indicate how a system changes. If you are interested in a particular initial condition ${\bf x}_0$, just find the corresponding position in the stream plot. The stream line that goes through that point in the stream plot indicates ${\bf x}(t)$.

## Think! 4: Interpreting Eigenvalues and Eigenvectors

Using some helper functions, we show the stream plots for each option of A that you examined in the earlier interactive demo. We included the eigenvectors of $\bf A$ as a red line (1st eigenvalue) and a blue line (2nd eigenvalue) in the stream plots.

What is special about the direction in which the principal eigenvector points? And how does the stability of the system relate to the corresponding eigenvalues? (Hint: Remember from your [introduction to linear algebra](https://www.youtube.com/watch?v=PFDu9oVAE-g&list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab&index=15&t=0s) that, for matrices with real eigenvalues, the eigenvectors indicate the lines on which $\bf Ax$ is parallel to $\bf x$ and real eigenvalues indicate the factor by which $\bf Ax$ is stretched or shrunk compared to $\bf x$.)

```{code-cell} python
:tags: [hide-input]
# @markdown Execute this cell to see stream plots

A_option_1 = np.array([[2, -5], [1, -2]])
A_option_2 = np.array([[3,4], [1, 2]])
A_option_3 = np.array([[-1, -1], [0, -0.25]])
A_option_4 = np.array([[3, -2], [2, -2]])

A_options = [A_option_1, A_option_2, A_option_3, A_option_4]
plot_specific_example_stream_plots(A_options)
```

:::{nma-explanation}
In top-left A, both eigenvalues are imaginary (no real component, the two
eigenvalues are complex conjugate pairs), so the solutions are all stable
oscillations. The eigenvectors are also complex conjugate pairs (that's why
we see them plotted on top of each other). They point in the direction of the
major axis of the elliptical trajectories.

In the top-right A, both eigenvalues are positive, so they are growing. The larger
eigenvalue direction (red) grows faster than the other direction (blue),
so trajectories all eventually follow the red eigenvector direction. Those that
start close to the blue direction follow blue for a bit initially.

In the bottom-left A, both eigenvalues are negative, so they are both decaying.
All solutions decay towards the origin [0, 0]. The red eigenvalue is larger in
magnitude, so decay is faster along the red eigenvector.

In the bottom-right A, one eigenvalue is positive (red) and one eigenvalue is negative
(blue). This makes the shape of the landscape the shape of a saddle (named after
the saddle that one puts on a horse for a rider). Trajectories decay along the
blue eigenvector but grows along the red eigenvector.
:::

:::{nma-feedback} Interpreting_Eigenvalues_and_Eigenvectors_Discussion
:::

---
# Summary

*Estimated timing of tutorial: 1 hour*

In this tutorial, we learned:

* How to simulate the trajectory of a dynamical system specified by a differential equation $\dot{x} = f(x)$ using a forward Euler integration scheme.
* The behavior of a one-dimensional linear dynamical system $\dot{x} = a x$ is determined by $a$, which may be a complex valued number. Knowing $a$, we know about the stability and oscillatory dynamics of the system.
* The dynamics of high-dimensional linear dynamical systems $\dot{\mathbf{x}} = \mathbf{A} \mathbf{x}$ can be understood using the same intuitions, where we can summarize the behavior of the trajectories using the eigenvalues and eigenvectors of $\mathbf{A}$.
