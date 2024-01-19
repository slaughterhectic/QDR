from flask import Flask, render_template, request, jsonify
import psycopg2
import openai


app = Flask(__name__)

# PostgreSQL configuration
db_config = "postgres://root:4fDCwsuZZCgowihAQzNLmTzeyeaoyppQ@dpg-cmkr88en7f5s73au5ol0-a.oregon-postgres.render.com/analyst_database"

# Connect to PostgreSQL using the provided connection string

openai.api_key = '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'

def get_table_names():
    conn = psycopg2.connect(db_config)
    cursor = conn.cursor()

    # Query to get table names
    cursor.execute(
        "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema'")

    table_names = [row[0] for row in cursor.fetchall()]

    conn.close()
    return table_names


def execute_query(query):
    conn = psycopg2.connect(db_config)
    cursor = conn.cursor()
    cursor.execute(query)

    # Fetch column names
    col_names = [desc[0] for desc in cursor.description]

    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return col_names, result

def generate_sql_query(prompt):
    # Use OpenAI API to generate SQL query
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=150
    )

    # Get the generated text and remove leading/trailing whitespaces
    generated_text = response['choices'][0]['text'].strip()
    # Replace line breaks with spaces
    generated_text = ' '.join(generated_text.splitlines())
    return generated_text
@app.route('/')
def index():
    # Fetch table names when rendering the index page
    table_names = get_table_names()
    return render_template('query_builder.html', table_names=table_names)


@app.route('/query', methods=['POST'])
def query():
    try:
        table_name = request.form['tableName']
        num_queries = int(request.form['numQueries'])
        condition = request.form['condition']
        at_least = int(request.form['atLeast'])
        at_most = int(request.form['atMost'])

        queries = []
        for i in range(1, num_queries + 1):
            field = request.form[f'field{i}']
            operator = request.form[f'operator{i}']
            value = request.form[f'value{i}']
            queries.append(f"{field} {operator} {value}")

        custom_modifications = request.form.getlist('customModifications[]')

        if condition == 'Any':
            query = f"SELECT * FROM {table_name} WHERE {' OR '.join(queries)}"
        elif condition == 'AtLeast':
            query = f"SELECT * FROM {table_name} WHERE {' AND '.join(queries)} LIMIT {at_least}"
        elif condition == 'AtMost':
            query = f"SELECT * FROM {table_name} WHERE {' AND '.join(queries)} LIMIT {1000 - at_most}"
        else:
            query = f"SELECT * FROM {table_name} WHERE {' AND '.join(queries)}"

        if custom_modifications:
            # If custom modifications are provided, generate the prompt
            prompt = f"strictly write a sql cmd to modify table {table_name} by {', '.join(custom_modifications)} for {', '.join(queries)}"

            # Use OpenAI to generate SQL query
            generated_query = generate_sql_query(prompt)
            result = execute_query(f"{generated_query}{query}")
            col_names, data = result
        else:
            # If no custom modifications, use the user-defined queries directly
            generated_query = query
            result = execute_query(query)
            col_names, data = result


        print(generated_query)
        print(query)


        return jsonify({'success': True, 'col_names': col_names, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True,port=5001)
