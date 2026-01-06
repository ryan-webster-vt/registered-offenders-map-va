import pandas as pd

def main():
    url = "https://worldpopulationreview.com/us-counties/virginia"
    df = pd.read_html(url)
    df = pd.DataFrame(df[0])

    total_pop_df = pd.DataFrame({
        'locality' : df['County'],
        'population' : df['2025 Pop. ↓']
    })

    total_pop_df.to_csv('data/total_population.csv')

if __name__ == '__main__':
    main()


