from flask import Flask, render_template, request, redirect, send_file
from scrapper import WebPageScraper
from xml.etree import ElementTree as ET
import json
import csv

app = Flask(__name__)
scraper = WebPageScraper(database_name='web_pages.db')


@app.route('/')
def index():
    return urls()


@app.route('/urls', methods=['GET', 'POST'])
def urls():
    if request.method == 'POST':
        # Handle form submission to insert a new URL
        new_url = request.form.get('new_url')
        if new_url:
            scraper.insert_new_url(new_url)

    pages_data = display_table('PAGES')

    return render_template('urls.html', pages_data=pages_data)


@app.route('/scrape')
def scrape():
    scraper.scrape_pages()
    pages_data = display_table('PAGES')

    return render_template('urls.html', pages_data=pages_data)


@app.route('/split')
def split():
    scraper.split_titles()
    pages_data = display_table('PAGES')

    return render_template('urls.html', pages_data=pages_data)


@app.route('/keywords', methods=['GET', 'POST'])
def keywords():
    if request.method == 'POST':
        # Handle form submission to insert a new keyword
        change_from = request.form.get('change_from')
        change_to = request.form.get('change_to')
        if change_from and change_to:
            scraper.insert_keyword_change(change_from, change_to)

        new_superfluous = request.form.get('new_superfluous')
        if new_superfluous:
            scraper.insert_superfluous_word(new_superfluous)
            redirect('/superfluous')

    keywords_data = display_table('KEYWORDS')

    return render_template('keywords.html', pages_data=keywords_data)


@app.route('/superfluous', methods=['GET', 'POST'])
def superfluous():
    if request.method == 'POST':
        new_superfluous = request.form.get('new_superfluous')
        if new_superfluous:
            scraper.insert_superfluous_word(new_superfluous)

    superfluous_data = display_table('SUPERFLUOUS')

    return render_template('superfluous.html', pages_data=superfluous_data)


@app.route('/changes', methods=['GET', 'POST'])
def changes():
    if request.method == 'POST':
        # Handle form submission to insert a new keyword
        change_from = request.form.get('change_from')
        change_to = request.form.get('change_to')
        if change_from and change_to:
            scraper.insert_keyword_change(change_from, change_to)

    changes_data = display_table('CHANGES')

    return render_template('changes.html', pages_data=changes_data)


@app.route('/clean', methods=['GET', 'POST'])
def clean():
    scraper.clean()
    keywords_data = display_table('KEYWORDS')

    return render_template('keywords.html', pages_data=keywords_data)


@app.route('/report', methods=['GET', 'POST'])
def report():
    keyword_data = scraper.get_keyword_report()

    return render_template('report.html', pages_data=keyword_data)


@app.route('/export')
def export():
    return render_template('export.html')


@app.route('/download_report/<format>')
def download_report(format):
    if format not in ['json', 'csv', 'xml']:
        return "Invalid format"

    if format == 'json':
        report_data = scraper.get_keyword_report()
        file_name = 'keyword_report.json'
        with open(file_name, 'w') as json_file:
            json.dump(report_data, json_file)

    elif format == 'csv':
        report_data = scraper.get_keyword_report()
        file_name = 'keyword_report.csv'
        with open(file_name, 'w', newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=report_data[0].keys())
            csv_writer.writeheader()
            csv_writer.writerows(report_data)

    elif format == 'xml':
        report_data = scraper.get_keyword_report()
        root = ET.Element('report')
        for entry in report_data:
            item = ET.SubElement(root, 'item')
            for key, value in entry.items():
                ET.SubElement(item, key).text = str(value)
        xml_data = ET.tostring(root, encoding='utf-8')
        file_name = 'keyword_report.xml'
        with open(file_name, 'wb') as xml_file:
            xml_file.write(xml_data)

    return send_file(file_name, as_attachment=True)


def display_table(table_name):
    connection = scraper.create_database_connection()
    cursor = connection.cursor()
    if table_name == 'KEYWORDS':
        cursor.execute(f'SELECT * FROM {table_name} ORDER BY keyword_count DESC')
    else:
        cursor.execute(f'SELECT * FROM {table_name}')
    data = cursor.fetchall()

    connection.close()
    return data


if __name__ == '__main__':
    app.run(debug=True)
