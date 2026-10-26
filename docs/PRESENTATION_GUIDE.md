# Presenting Association Lab

The opening screen introduces the question, shows a real association from the current results, and links directly to the main workflows. The sidebar groups every existing feature into getting started, exploration, and tools. Use **Ctrl+K** (or **⌘K** on macOS) to find a section during your presentation.

## Before you begin

- Build the current interface with `npm ci` and `npm run build` inside `frontend/` if it has not been built already.
- Launch the project as described in the README, then open **http://127.0.0.1:8000**. Keep its server running.
- Fonts are included locally. Viewing the prepared analysis does not require Google Fonts or a third-party service.
- Choose the light or dark theme using the moon/sun button. Use your browser's fullscreen mode for projection.

## Show a broader set of disease associations

Choose **Extended · Symptoms & diseases** at the top of the page. Its prepared analysis covers 40 of 41 disease labels. Open **Disease associations**, select **Dengue** or **Malaria**, read a rule, then download the selected source's PDF. Switch back to **Original · Patient profiles** to show that its data, defaults, and saved results are separate.

The coverage badge updates with the selected analysis. The extended source has 304 distinct symptom profiles after removing repeated benchmark rows; it does not include demographics or recorded negative symptoms. Explain this distinction when comparing the two sources.

## A five-minute live demonstration

1. **Start here:** introduce the project as a way to find features that appear together. Point to the retained-profile count, combination count, and the real association diagram.
2. **Explore the dataset:** change the attribute to Gender or Age Group and hover over a bar. Explain that each count refers to recorded profiles.
3. **Check the data:** compare source and retained rows, then show the cleaning decisions and column audit.
4. **Disease associations:** read all left-side conditions together, then the right-side disease label. Explain support, confidence, and lift with the worked example and its actual supporting record count.
5. **Explore patterns:** choose **Fever: Yes** under **Contains a condition**, show the matching-rule count, sort by a metric, then choose **Reset filters**. Use **Understand the charts** to compare rules visually.
6. **Download reports:** download the PDF or a CSV to demonstrate a complete path from exploration to a deliverable.

For a more structured explanation, choose **Start guided tutorial**. Each of its six steps opens the working section and provides a **Back to tutorial** button that preserves your place.

**Analysis settings** still supports changing thresholds and running Apriori locally. A new run replaces the saved results and report; the prepared analysis is sufficient for the demonstration. Vercel deployments retain their existing read-only analysis behavior.

Associations describe this sample. They do not establish medical causes, diagnose a patient, or demonstrate diagnostic accuracy.


The primary pages show charts and short labels. Open the information icons or expandable rows for methodology and explanations. Ranked charts display the full association beside each bar, and **Disease in charts** selects the disease being compared. Category, condition, combination, and display-threshold filters are all menu based. Analysis settings uses preset values initially; **Custom values** enables the full numeric controls.


Long tables use 10-row pages. **Previous** and **Next** browse the selected results; the **Rows to show** menu sets the selection limit, and Filtered CSV exports that entire selection. The chart ranking can be switched between **By lift** and **By confidence** without repeating the same associations in two separate lists.
