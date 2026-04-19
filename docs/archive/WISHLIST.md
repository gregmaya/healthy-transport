## Healthy Transport : whishlist

### Top priority (must debugs)
- The current phase highlightes an imbalance on the data availability of Frederiksberg DAR entrances (89 points, from `add_frederiksberg_dar.py`). This is only a fraction of the buildings with actual entrances, which is creating a major missinterpretations of the neighbouring areas of the study. We need to find a way in which the thre population segments are equally interpolated into building entrances such that the scoring calculations on the bus routes within the AOI do not suffer from edge effects.

- We need to unify/relable the two macro scoring scenarios **Baseline score** (catchment areas) and the **Health score** (with actual population distribution). Stay consistent with the languance all across (update buttons, titles, chart axis names, info panels)

- Bus interactive tool: **The green path access.** The ides is to calculate the aggregate percentage of the trips that pass through green areas. 
    - data needed: 1. green area polygons (I believe already in repo), 2. population interpolation completed at the address level. 
    - method: 1. To every 20m network segment assign the length that falls within a green area (values could range from 0 to 20) 2. using the same cityseer method (`compute_stats`) we neeed to calulate the following for each path : total path lenght and green path lenght. 3. considering the different population speeds, calculate the total time of the journey + the time spent in green areas.
    - when displayed it need to show 2 things: **TIME** the average time spent in 'green walking' (when HEALTH SCORE), plus the **PATH JOURNEY** (find a better name) to show the percentage of the paths in green (when BASELINE). 
    - The display should have one fixed bar for the entire AOI and another one underneath with the same metrics but only for the selected bus stop (dynamic)

- Bus interactive tool: **Population** we need to update the figures per neighbourhood with real data.
    - Note: The current dropdown of the sub-district (neighbourhood ) could be 'upgraded' to be a more global 'highlighter' that applies to all other features in the dashboard (not a filter but a highlighter that puts into perspective the neighbourhood numbers vs.the entire Norrebro district). This probably requires a deeper exploration so could be added to the MEDIUM priority. In any case the dropdown needs to shift from being on the population section only, to the top where the current SCORE MODE is displayed : to be something like '**Health score** in [dropdown]'


___
### Medium Priority (industry diferentiators)

- The entire tool is called HEALTHY TRANSPORT hence I believe the top navigation bar should start with that and all the transport options be right aligned. opposite to what they currently are. ALL SECTIONS 'under development' should not finish with 'explore the map' as those dashboards will need to be different to the current one of the buses. remove that CTA

- Bus interactive tool: The scatterplot. currently the axis rages are dynamic such that for every population segment the axis rescale. they should be static from 0 -1 on both axis marking only every 0.25 increments. Also, (just like the colours change for the points of the map when changing the score mode) the points on the scatterplot should also respond to the control changes of score modes on the left. 


### UX/UI: 
- map tooltip: replace the 'long form' table of segment population into a 'wide table' with population labels as column headers (row 1) and the scores underneath. use modern gridlines when appropriate. 

- Change the SCORE MODE BUTTONS to a very clear TOGGLE (no button)

- text change: from 'Infrastructure potential — shortest paths to all address points, equal weight per resident.' to something shorter, simpler, less technical. 

- In the scrollable section, is it possible to add a background behind the cards? If so, I'd like to expand the map to cover all the screen so the cards show floating on top of the map. This only applies to the cards currently displayed with the map (4-5-6).

- **info pop-us**: (1) needs revision to be up to date, and (2) the popups are greyed out by the same opacity as the rest of the tool when they appear. Ideally they should be on top of that opacity layer as they are the focus of that moment. 

___
### Low Priority (nice to haves)

- Three parameters should be exposed as **interactive sliders** in the tool: (i) Peak distance, (ii) Decay steepness, (iii) Zero-benefit threshold. This lets planners test sensitivity and adapt the model to local context.