# Notebooks

Jupyter notebooks for exploratory data analysis, visualization, and prototyping.

## Naming Convention

Use numbered prefixes for sequential workflows:

```
01_data_exploration_buildings.ipynb
02_data_exploration_roads.ipynb
03_population_assignment.ipynb
10_network_analysis.ipynb
20_accessibility_analysis.ipynb
30_health_correlations.ipynb
99_final_visualizations.ipynb
```

## Organization

- **00-09**: Data exploration and quality assessment
- **10-19**: Data processing and integration
- **20-29**: Analysis (accessibility, networks, spatial)
- **30-39**: Health metrics and correlations
- **90-99**: Final outputs, reports, visualizations

## Best Practices

1. **Document as you go**: Add markdown cells explaining each step
2. **Keep notebooks focused**: One analysis per notebook
3. **Export key functions**: Move reusable code to `src/` modules
4. **Save outputs**: Export figures to `reports/figures/`
5. **Clear outputs before committing**: Use `jupyter nbconvert --clear-output`

## Environment

Ensure all required packages are listed in `requirements.txt` at the project root.
