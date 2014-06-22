#!/usr/bin/env python3
import config
import smtplib
import ssl
import sys
import time
import urllib.error, urllib.parse, urllib.request
from bs4 import BeautifulSoup
from datetime import datetime

last_page = ''

class ClassyUrlOpener(urllib.request.FancyURLopener):
  version = 'Mozilla/5.0 (X11; Linux x86_64; rv:21.0) Gecko/20100101 Firefox/21.0'

def log(msg):
  print('[%s] %s' % (datetime.now(), msg))

def parse(expr, contents):
  doc = BeautifulSoup(contents)
  return doc.select(expr)

def fetch(url, post_data=None):
  if post_data is None:
    post_data = {}

  encoded_post = urllib.parse.urlencode(post_data).encode('ascii')
  u = urllib.request.urlopen(url, encoded_post)
  contents = u.read().decode('utf8')
  u.close()

  last_page = contents
  return contents

def configure_cookie_handling():
  ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv3)
  opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(),
    urllib.request.HTTPSHandler(context=ssl_context)
  )
  urllib.request.install_opener(opener)

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
    'CLASS_SRCH_WRK2_INSTITUTION$31$': 'UCALG',
    'CLASS_SRCH_WRK2_STRM$35$': term,
    'CLASS_SRCH_WRK2_SUBJECT$108$': subject_name,
    'CLASS_SRCH_WRK2_CATALOG_NBR$8$': course_name,
    # Values: 'C'=contains, 'E'=exact match
    'CLASS_SRCH_WRK2_SSR_EXACT_MATCH1': 'E',
    'CLASS_SRCH_WRK2_ACAD_CAREER': '',
    'CLASS_SRCH_WRK2_SSR_OPEN_ONLY$chk': 'N',
    'CLASS_SRCH_WRK2_OEE_IND$14$$chk': 'N',
  })

  resp = fetch(course_search_url, params)
  return resp


def fetch_full_search_results(course_search_url, partial_search_results):
  params = {
    'ICAJAX': '1',
    'ICType': 'Panel',
    'ICElementNum': '0',
    'ICStateNum': '57',
    'ICAction': '$ICField106$hviewall$0',
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
  search_form_url = urllib.parse.unquote(target_content['src'])

  # Fetch class search form.
  pages['course_search'] = fetch(search_form_url)

  course_search_url = 'https://prdrps2.ehs.ucalgary.ca/psc/saprd/' + \
                     'EMPLOYEE/HRMS/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL'

  # Fetch initial set of search results.
  pages['search_results_partial'] = fetch_initial_search_results(
    course_search_url, term, subject_name, course_name, pages['course_search']
  )

  # Fetch full set of search results.
  # TODO: for classes where all results are on first page (i.e., those with <=
  # 3 sections), do not perform this query, but instead simply use
  # search_results_partial.
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
  # Remove XML bullshit so BeautifulSoup can parse document. Hacky, but works.
  doc_start = contents.find('<table')
  contents = contents[doc_start:]

  doc = BeautifulSoup(contents)
  table_rows = doc.select('table[id=ACE_$ICField106$0] tr')

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

def resolve_section_names(desired_sections_names, all_sections):
  if desired_sections_names == 'all':
    all_section_names = [section['name'] for section in all_sections]
    return all_section_names
  else:
    return desired_sections_names

def find_open_sections(subject_name, course_name, all_sections, query_sections_names):
  all_sections_names = [section['name'] for section in all_sections]
  invalid_sections_names = set(query_sections_names) - set(all_sections_names)

  if len(invalid_sections_names) > 0:
    raise Exception('Invalid %s %s sections: %s' % (
      subject_name,
      course_name,
      ', '.join(invalid_sections_names)
    ))

  # Note that it's not enough to merely check that a section's status is
  # "open", as a section may be "open", "closed", or "wait list". We wish to
  # notify whenever it's not closed.
  open_sections = [section for section in all_sections if
    section['name'] in query_sections_names and
    section['status'] != 'closed']
  return open_sections

def generate_notification(subject_name, course_name, open_sections):
  notification = ''
  for section in open_sections:
    notification += '%s %s %s: %s\n' % (
      subject_name,
      course_name,
      section['name'],
      section['status'],
    )
  return notification

def send_email(to_addr, subject, body):
  headers = {
    'From': '"%s" <%s>' % (config.email_from_name, config.email_from_addr),
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

  log('Sent "%s" to %s.' % (subject, to_addr))

# Note that this count won't be entirely accurate, as 'all' will resolve to one
# query, rather than all sections composing that class. For the use of this
# function, however, that's quite all right, as we only want to determine
# whether the value is zero.
def count_queries(query_sections):
  query_count = 0
  for query_section in query_sections.values():
    query_count += len(query_section)
  return query_count

def main():
  configure_cookie_handling()
  first_iteration = True

  while count_queries(config.query_sections) > 0:
    for user, user_queries in config.query_sections.items():
      notification = ''
      open_classes = []
      open_class_indices = [] # Used to delete classes once found.

      for class_index in range(len(user_queries)):
        if first_iteration:
          first_iteration = False
        else:
          # Sleep first so that e-mail notification won't be delayed if this is last course user wants checked.
          time.sleep(config.seconds_between_checks)

        query = user_queries[class_index]
        subject = query['subject_name']
        course = query['course_name']
        desired_sections_names = query['sections']

        results_page = determine_course_status(subject, course, query['term'])
        all_sections = parse_section_list(results_page)
        query_sections_names = resolve_section_names(desired_sections_names, all_sections)
        open_sections = find_open_sections(subject, course, all_sections, query_sections_names)

        if len(open_sections) > 0:
          open_class_indices.append(class_index)
          notification += generate_notification(subject, course, open_sections)
          open_classes.append('%s %s' % (subject, course))

        log('Queried %s %s for %s. %s/%s section(s) are open [%s total].' % (
          subject,
          course,
          user,
          len(open_sections),
          len(query_sections_names),
          len(all_sections),
        ))

      notification = notification.strip()
      if len(notification) > 0:
        subject = 'Open course notification: %s' % ', '.join(open_classes)
        send_email(user, subject, notification)

      # Remove open classes so they're no longer queried. Iterate in reverse
      # sorted order so that earlier-deleted indices do not change the entries
      # referenced by later-deleted ones.
      #
      # Note that classes are removed wholesale if *any* of the user's desired
      # sections are open. This means that none of the other sections of
      # interest for that class will continue to be queried.
      for open_index in reversed(sorted(open_class_indices)):
        log('Removing %s %s from %s\'s queries.' % (
          user_queries[open_index]['subject_name'],
          user_queries[open_index]['course_name'],
          user
        ))
        del user_queries[open_index]

  print('No remaining sections to query.')
  sys.exit(0)

if __name__ == '__main__':
  while True:
    try:
      main()
    except (urllib.error.URLError, ConnectionError) as e:
      log('Exception: %s' % e)
      with open('log', 'w') as f:
        f.write('Exception: %s\n' % e)
        sep = 80*'=' + '\n'
        f.write(sep)
        f.write(last_page)
        f.write(sep + 2*'\n')
      time.sleep(300)
