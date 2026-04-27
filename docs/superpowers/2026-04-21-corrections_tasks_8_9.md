The following things where not addressed, or incorrectly completed during the realisarion of the plan docs/superpowers/specs/2026-04-20-right-panel-neighbourhood-redesign.md.

This refers to a larger development plan described in PROGRESS.md

## BUGS
- **task 4 Floating mode toggle (#mode-toggle-float) at top-centre** : it was correctly removed from the left panel but it's currently not showing anywhere. AS mentioned it needs to be a central element while navigating the interactive tool. 

- No green parks in Friederiksberg. This is underrepresenting the figures and misscalculating the green paths going through that area.

## Improvements
- **taks 5 Collapsible left panel**: the current UI element is not clear that the collapsable behaviour is doable. please review the element (button) for both behaviours collapsing and expanding. 

- **TOP dropdown** [activeNeighbourhood] : (i) remove the outside box so that it looks more like a title yet the dropdown behaviour continues. (ii) In the map the polygons should be light greys (high opacity) behind all other layers with no edge colour (i.e. remove current orange).

- **DISTRIBUTION** section . (i) remove subtitle "Distribution". (ii) The behaviour when [activeNeighbourhood] is not the entire NORREBRO each of the bars should have a way to display both the share of stops in NORREBRO (maybe something like black line) and [activeNeighbourhood]

eg. NORREBRO
```
Low benefit     XXXXXXXXX::::::::: 19%
...
```

eg. GULDERBERGSKVARTERET
```
Low benefit     XXXXX::|:::::::::: 11% <- '|' BLACK MARKER representing the entire Norrebro district
...
```

- **SCATTERPLOT** the axis need to be fixed always 0-1 with stops every 0.25. Y axis titles should be Health Score (All/Children/Working age/elderly)

- **task6 merged People + Green Block** currently it's not serioue enough. remove all emojis. and reshape for it to display the figures in the following way : Population column based on the [activeNeighbourhood]   // Green Column (Click-based section )
The width split does not need to be 50/50 probably more like 70/30 ans no vertical division should be visible.


```
(Remove any subtitle "People + Green Access")
|----------------------------------|---------------------------------------|  Fixed section
|             ###                  |            (## min / ## %)            | <-- BLACK Large bold fonts
| people in [activeNeighbourhood]  | (avg. min in green / paths in green)  |  
|----------------------------------|---------------------------------------| Click-based section [selectedStop]
|             ###  (± ##%)         |            (## min / ## %)            | <-- GREY Large bold fonts
|       people in catchment        | (avg. min in green / paths in green)  | <-- figures from, the selectedStop
|----------------------------------|---------------------------------------| Fixed section
| Children 0-14                    |            (## min / ## %)            |
| XXXXXXXXXX::::::::::: (± ##%)    | (avg. min in green / paths in green)  | <-- GREEN smaller fonts
|                                  |                                       |
| Working age 15-64                |            (## min / ## %)            |
| XXXXXXXXXXXXXXXXXX::: (± ##%)    | (avg. min in green / paths in green)  | <-- GREEN smaller fonts
|                                  |                                       |
| Elderly  65+                     |            (## min / ## %)            |
| XXXXXXX:::::::::::::: (± ##%)    | (avg. min in green / paths in green)  |<-- GREEN smaller fonts
|----------------------------------|---------------------------------------|
(remove 'Population model estimates methodology' )
```
 (± ##%) error rate (ideally also evident in the horizontal bars)

Part of the current problem is that the default size of the panel is making the columns to be staked.

- **Stop colours** while the catchment state is enaled needs revising because they show all blue. Most likely becuase it's using the same range as the health one but the actual values vary drastically as we saw.

## Additionals

- in left panel, I would like to have the option to use the people in catchment or the green numbers (time or path share) to control the size of the stops. The default should be homogenous sizes just like they currently are.

- just like there currently is a stop on the zoom out there also needs to be a zoom in the zoom in 