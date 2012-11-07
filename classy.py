#!/usr/bin/env python2
import config
import smtplib
import time
import urllib
import urllib2
from bs4 import BeautifulSoup
from datetime import datetime

def log(msg):
  print '[%s] %s' % (datetime.now(), msg)

def parse(expr, contents):
  doc = BeautifulSoup(contents)
  return doc.select(expr)

def fetch(url, post_data=None):
  if post_data is None:
    post_data = {}

  headers = {'User-Agent': 'A large hard-breathing middle-aged slow man'}
  u = urllib2.urlopen(urllib2.Request(url, urllib.urlencode(post_data), headers))
  contents = u.read()
  u.close()
  return contents

def configure_cookie_handling():
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
  urllib2.install_opener(opener)

def extract_hidden(contents):
  hidden_elems = parse('form[name=win0] input[type=hidden]', contents)
  hidden = {}
  for elem in hidden_elems:
    hidden[elem['name']] = elem['value']
  return hidden

def fetch_initial_search_results(
  course_search_url, term, subject_name,
  course_name, course_search_page
):
  hidden = extract_hidden(course_search_page)

  params = dict(hidden)
  params.update({
    'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH',
    'CLASS_SRCH_WRK2_INSTITUTION$49$': 'UCALG',
    'CLASS_SRCH_WRK2_STRM$52$': term,
    'CLASS_SRCH_WRK2_SUBJECT$65$': subject_name,
    'CLASS_SRCH_WRK2_CATALOG_NBR$73$': course_name,
    # Values: 'C'=contains, 'E'=exact match
    'CLASS_SRCH_WRK2_SSR_EXACT_MATCH1': 'E',
    'CLASS_SRCH_WRK2_ACAD_CAREER': '',
    'CLASS_SRCH_WRK2_SSR_OPEN_ONLY$chk': 'N',
    'CLASS_SRCH_WRK2_OEE_IND$76$$chk': 'N',
  })

  return fetch(course_search_url, params)

def fetch_full_search_results(course_search_url, partial_search_results):
  params = {
    'ICAJAX': '1',
    'ICType': 'Panel',
    'ICElementNum': '0',
    'ICStateNum': '30',
    'ICAction': '$ICField110$hviewall$0',
    'ICXPos': '0',
    'ICYPos': '0',
    'ICFocus': '',
    'ICSaveWarningFilter': '0',
    'ICChanged': '-1',
    'ICResubmit': '0',
    'ICModalWidget': '0',
    'ICZoomGrid': '0',
    'ICZoomGridRt': '0',
    'ICModalLongClosed': '',
    'ICActionPrompt': 'false',
    'ICFind': '',
    'ICAddCount': '',
  }

  dynamic_keys = ('ICSID', 'ICStateNum')
  dynamic_params = {}
  for key in dynamic_keys:
    dynamic_params[key] = parse('form[name=win0] input[name=%s]' % key,
      partial_search_results)[0]['value']
  params.update(dynamic_params)

  return fetch(course_search_url, params)

def determine_course_status(subject_name, course_name, term):
  pages = {}

  # PeopleSoft stores all pages in iframe whose src is continually modified.
  # Fetch the page inside this iframe.
  pages['container'] = fetch('https://prdrps2.ehs.ucalgary.ca/psauthent/class-search/public')
  target_content = parse('[name=TargetContent]', pages['container'])[0]
  search_form_url = urllib.unquote(target_content['src'])

  # Fetch class search form.
  pages['course_search'] = fetch(search_form_url)

  course_search_url = 'https://prdrps2.ehs.ucalgary.ca/psc/saprd/' + \
                     'EMPLOYEE/HRMS/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL'

  # Fetch initial set of search results.
  pages['search_results_partial'] = fetch_initial_search_results(
    course_search_url, term, subject_name, course_name, pages['course_search']
  )

  # Fetch full set of search results.
  pages['search_results_full'] = fetch_full_search_results(
    course_search_url, pages['search_results_partial']
  )
  return pages['search_results_full']

def generate_search_elements(row):
  elements = {}
  elements['section_name'] = row.find( lambda tag:
    tag.name == 'a' and
    tag.has_attr('name') and
    tag['name'].startswith('DERIVED_CLSRCH_SSR_CLASSNAME_LONG')
  )
  elements['status_image'] = row.find(lambda tag:
    tag.name == 'img' and
    tag.parent.parent.has_attr('id') and
    tag.parent.parent['id'].startswith('win0divDERIVED_CLSRCH_SSR_STATUS_LONG')
  )
  elements['section_group'] = row.find(lambda tag:
    tag.name == 'span' and
    tag.has_attr('id') and
    tag['id'].startswith('UCSS_E010_WRK_ASSOCIATED_CLASS')
  )
  elements['daytime'] = row.find(lambda tag:
    tag.name == 'span' and
    tag.has_attr('id') and
    tag['id'].startswith('MTG_DAYTIME')
  )
  elements['room'] = row.find(lambda tag:
    tag.name == 'span' and
    tag.has_attr('id') and
    tag['id'].startswith('MTG_ROOM')
  )
  elements['instructor'] = row.find(lambda tag:
    tag.name == 'span' and
    tag.has_attr('id') and
    tag['id'].startswith('MTG_INSTR')
  )
  elements['period'] = row.find(lambda tag:
    tag.name == 'span' and
    tag.has_attr('id') and
    tag['id'].startswith('MTG_TOPIC')
  )
  return elements

def parse_section_list(contents):
  doc = BeautifulSoup(contents)
  table_rows = doc.select('table[id=ACE_$ICField110$0] tr')

  section_list = []
  for i in range(len(table_rows)):
    row = table_rows[i]
    elements = generate_search_elements(row)
    text = row.get_text()

    if elements['status_image'] is not None:
      section_list.append({})
      section = section_list[-1]
      section['status'] = elements['status_image']['alt'].lower()
    elif elements['section_name'] is not None:
      section_name_and_id = elements['section_name'].get_text()
      elems = section_name_and_id.split('(', 1)
      section['name'] = elems[0]
      section['id'] = elems[1][:-1] # Remove trailing ')'.
    else:
      for key in ('section_group', 'daytime', 'room', 'instructor', 'period'):
        if elements[key] is not None:
          section[key] = elements[key].get_text()

  # Convert numerical strings to integers.
  for i in range(len(section_list)):
    for k in section_list[i].keys():
      if section_list[i][k].isdigit():
        section_list[i][k] = int(section_list[i][k])

  return section_list

def generate_notification(subject_name, course_name, sections, query_sections):
  # Note query_sections can be 'all'.
  all_section_names = [section['name'] for section in sections]
  if query_sections == 'all':
    query_sections = all_section_names

  invalid_sections = set(query_sections) - set(all_section_names)
  if len(invalid_sections) > 0:
    raise Exception('Invalid %s %s sections: %s' % (
      subject_name,
      course_name,
      ', '.join(invalid_sections)
    ))

  notification = ''
  for section in sections:
    if section['name'].upper() in query_sections and section['status'] == 'open':
      notification += '%s %s %s: %s\n' % (
        subject_name,
        course_name,
        section['name'],
        section['status'],
      )
  return notification

def send_email(to_addr, subject, body):
  headers = {
    'From': config.email_from_addr,
    'To': to_addr,
    'Subject': subject,
  }
  header_text = ''
  for key in headers:
    header_text += '%s: %s\n' % (key, headers[key])
  header_text = header_text.strip()

  session = smtplib.SMTP(config.email_host, config.email_port)
  session.ehlo()
  session.starttls()
  session.login(config.email_username, config.email_password)
  session.sendmail(config.email_from_addr, to_addr, header_text + 2*'\r\n' + body)

  log('Sent "%s" to %s' % (subject, to_addr))

def main():
  configure_cookie_handling()
  first_iteration = True

  while True:
    for user, user_queries in config.query_sections.items():
      notification = ''
      for qs in user_queries:
        if first_iteration:
          first_iteration = False
        else:
          # Sleep first so that e-mail notification won't be delayed if this is last course user wants checked.
          time.sleep(config.seconds_between_checks)

        results_page = determine_course_status(qs['subject_name'], qs['course_name'], qs['term'])
        sections = parse_section_list(results_page)
        notification += generate_notification(qs['subject_name'], qs['course_name'],
          sections, qs['sections'])

        open_section_count = len([section for section in sections if section['status'] == 'open'])
        log('Queried %s %s for %s. %s/%s sections are open.' % (qs['subject_name'], qs['course_name'], user, open_section_count, len(sections)))

      notification = notification.strip()
      if len(notification) > 0:
        send_email(user, 'Open course notification', notification.strip())

if __name__ == '__main__':
  main()
