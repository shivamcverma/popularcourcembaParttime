from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import re
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PCOMBA_O_URL="https://www.shiksha.com/part-time-mba-pgdm-chp"

PCOMBA_Q_URL = "https://www.shiksha.com/tags/mba-pgdm-tdp-422"
PCOMBA_QD_URL="https://www.shiksha.com/tags/mba-pgdm-tdp-422?type=discussion"


def create_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# ---------------- UTILITIES ----------------
def scroll_to_bottom(driver, scroll_times=3, pause=1.5):
    for _ in range(scroll_times):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(pause)




def scrape_chp_overview_section(driver):
    driver.get(PCOMBA_O_URL)
    soup = BeautifulSoup(driver.page_source, "html.parser")


    section = soup.select_one("section#chp_section_overview")
    if not section:
        return {}

    data = {
        "title":"",
        "updated_on": None,
        "author": None,
        "designation":"",
        "overview": None,
        "course_highlights": {},
        "faqs": []
    }
    title = soup.find("div",class_="a54c")
    h1 = title.text.strip()
    data["title"]=h1
    # -------------------------
    # Updated Date
    # -------------------------
    updated_el = section.select_one(".f48b span")
    if updated_el:
        data["updated_on"] = updated_el.get_text(strip=True)

    # -------------------------
    # Author
    # -------------------------
    author_el = section.select_one(".be8c a")
    if author_el:
        data["author"] = author_el.get_text(strip=True)
    
    span = soup.find("span",class_="b0fc")
    data["designation"]=span.text.strip()

    # -------------------------
    # Overview (Heading + Intro Paras)
    # -------------------------
    overview_el = section.select_one("div.wikkiContents.faqAccordian")
    if overview_el:
        overview_parts = []

        content_div = overview_el.find("div", recursive=False)
        if content_div:
            for tag in content_div.find_all(["h2", "p"], recursive=False):
                text = tag.get_text(" ", strip=True)

                if not text:
                    continue
                if "Suggested Read" in text:
                    break  # stop once suggested read starts

                overview_parts.append(text)

        data["overview"] = " ".join(overview_parts[:3])

    # -------------------------
    # Course Highlights
    # -------------------------
    table = section.select_one("table")
    if table:
        for row in table.select("tr")[1:]:
            cols = row.select("td")
            if len(cols) == 2:
                key = cols[0].get_text(" ", strip=True)
                value = cols[1].get_text(" ", strip=True)
                data["course_highlights"][key] = value

    # -------------------------
    # FAQs
    # -------------------------
    questions = section.select("div.sectional-faqs > div.html-0")

    for q in questions:
        question = q.get_text(" ", strip=True).replace("Q:", "").strip()
        answer_block = q.find_next_sibling("div", class_="_16f53f")
        if not answer_block:
            continue

        answer = answer_block.select_one(".cmsAContent")
        if answer:
            data["faqs"].append({
                "question": question,
                "answer": answer.get_text(" ", strip=True)
            })
    # -------------------------
    # Eligibility Section
    # -------------------------
    elig_section = soup.select_one("section#chp_section_eligibility")
    if elig_section:
        eligibility_data = {
            "title": "",
            "content": [],
            "faqs": []
        }

        # Section Title
        h2 = elig_section.select_one("h2.tbSec2")
        if h2:
            eligibility_data["title"] = h2.get_text(strip=True)

        # Main content (p, h2, ul)
        content_block = elig_section.select_one("div.wikkiContents.faqAccordian > div")
        if content_block:
            for tag in content_block.find_all(["p", "h2", "ul"], recursive=False):
                text = tag.get_text(" ", strip=True)
                if text:
                    eligibility_data["content"].append(text)

        # FAQs
        faq_questions = elig_section.select("div.sectional-faqs > div.html-0")
        for q in faq_questions:
            question = q.get_text(" ", strip=True).replace("Q:", "").strip()
            answer_block = q.find_next_sibling("div", class_="_16f53f")
            if not answer_block:
                continue

            answer = answer_block.select_one(".cmsAContent")
            if answer:
                eligibility_data["faqs"].append({
                    "question": question,
                    "answer": answer.get_text(" ", strip=True)
                })

        data["eligibility_section"] = eligibility_data
    # -------------------------
    # Popular Exams Section
    # -------------------------
    pop_section = soup.select_one("section#chp_section_popularexams")
    if pop_section:
        pop_data = {
            "title": "",
            "intro": "",
            "exams": [],
            "important_dates": {
                "upcoming": [],
                "past": []
            },
            "faqs": []
        }

        # Section Title
        h2 = pop_section.select_one("h2.tbSec2")
        if h2:
            pop_data["title"] = h2.get_text(strip=True)

        # Intro paragraph
        intro_p = pop_section.select_one("div.wikkiContents.faqAccordian p")
        if intro_p:
            pop_data["intro"] = intro_p.get_text(" ", strip=True)

        # Entrance Exams Table
        exam_table = pop_section.select_one("div.wikkiContents table")
        if exam_table:
            for row in exam_table.select("tr")[1:]:
                cols = row.select("td")
                if len(cols) == 2:
                    exam_name = cols[0].get_text(" ", strip=True)
                    link_tag = cols[1].select_one("a")
                    pop_data["exams"].append({
                        "exam": exam_name,
                        "link": link_tag["href"] if link_tag else None
                    })

        # Important Exam Dates - Upcoming
        upcoming_table = pop_section.select_one("table.upcomming-events")
        if upcoming_table:
            for row in upcoming_table.select("tr")[1:]:
                cols = row.select("td")
                if len(cols) == 2:
                    pop_data["important_dates"]["upcoming"].append({
                        "date": cols[0].get_text(" ", strip=True),
                        "event": cols[1].get_text(" ", strip=True)
                    })

        # Important Exam Dates - Past
        past_table = pop_section.select_one("table.upcomming-events.past-events")
        if past_table:
            for row in past_table.select("tr")[1:]:
                cols = row.select("td")
                if len(cols) == 2:
                    pop_data["important_dates"]["past"].append({
                        "date": cols[0].get_text(" ", strip=True),
                        "event": cols[1].get_text(" ", strip=True)
                    })

        # FAQs
        faq_questions = pop_section.select("div.sectional-faqs > div.html-0")
        for q in faq_questions:
            question = q.get_text(" ", strip=True).replace("Q:", "").strip()
            answer_block = q.find_next_sibling("div", class_="_16f53f")
            if not answer_block:
                continue

            answer = answer_block.select_one(".cmsAContent")
            if answer:
                pop_data["faqs"].append({
                    "question": question,
                    "answer": answer.get_text(" ", strip=True)
                })

        data["popular_exams_section"] = pop_data
    # -------------------------
    # Popular Specialization Section
    # -------------------------
    spec_section = soup.select_one("section#chp_section_popularspecialization")
    if spec_section:
        spec_data = {
            "title": "",
            "intro": "",
            "specializations_table": [],
            "relevant_links": [],
            "popular_specializations": [],
            "faqs": []
        }

        # Section Title
        h2 = spec_section.select_one("h2.tbSec2")
        if h2:
            spec_data["title"] = h2.get_text(strip=True)

        # Intro Paragraph
        intro_p = spec_section.select_one("div.wikkiContents p")
        if intro_p:
            spec_data["intro"] = intro_p.get_text(" ", strip=True)

        # Specialization Table
        table = spec_section.select_one("div.wikkiContents table")
        if table:
            for row in table.select("tr")[1:]:
                cols = row.select("td")
                for col in cols:
                    link = col.select_one("a")
                    spec_data["specializations_table"].append({
                        "name": col.get_text(" ", strip=True),
                        "link": link["href"] if link else None
                    })

        # Relevant Links
        for p in spec_section.select("div.wikkiContents p a"):
            spec_data["relevant_links"].append({
                "title": p.get_text(strip=True),
                "link": p["href"]
            })

        # Popular Specializations Box
        for li in spec_section.select("ul.specialization-list li"):
            name_tag = li.select_one("a")
            count_tag = li.select_one("p")
            spec_data["popular_specializations"].append({
                "name": name_tag.get_text(strip=True) if name_tag else "",
                "link": name_tag["href"] if name_tag else None,
                "college_count": count_tag.get_text(strip=True) if count_tag else ""
            })

        # FAQs
        faq_questions = spec_section.select("div.sectional-faqs > div.html-0")
        for q in faq_questions:
            question = q.get_text(" ", strip=True).replace("Q:", "").strip()
            ans_block = q.find_next_sibling("div", class_="_16f53f")
            if not ans_block:
                continue

            answer = ans_block.select_one(".cmsAContent")
            if answer:
                spec_data["faqs"].append({
                    "question": question,
                    "answer": answer.get_text(" ", strip=True)
                })

        data["popular_specialization_section"] = spec_data

    # -------------------------
    # Course Syllabus Section
    # -------------------------
    syllabus_section = soup.select_one("section#chp_section_coursesyllabus")
    if syllabus_section:
        syllabus_data = {
            "title": "",
            "intro": [],
            "core_subjects": [],
            "elective_subjects": [],
            "note": "",
            "related_links": [],
            "faqs": []
        }

        # Title
        h2 = syllabus_section.select_one("h2.tbSec2")
        if h2:
            syllabus_data["title"] = h2.get_text(strip=True)

        # Intro paragraphs
        for p in syllabus_section.select("div.wikkiContents > div > p"):
            syllabus_data["intro"].append(p.get_text(" ", strip=True))

        # Syllabus Table
        table = syllabus_section.select_one("table")
        if table:
            rows = table.select("tr")
            current_section = "core"

            for row in rows:
                headers = row.select("th")
                if headers:
                    if "Elective" in headers[0].get_text():
                        current_section = "elective"
                    continue

                cols = row.select("td")
                for col in cols:
                    subject = col.get_text(strip=True)
                    if subject and subject != "-":
                        if current_section == "core":
                            syllabus_data["core_subjects"].append(subject)
                        else:
                            syllabus_data["elective_subjects"].append(subject)

        # Note
        note = syllabus_section.select_one("em")
        if note:
            syllabus_data["note"] = note.get_text(" ", strip=True)

        # Related links
        for a in syllabus_section.select("div.wikkiContents a"):
            syllabus_data["related_links"].append({
                "title": a.get_text(strip=True),
                "link": a.get("href") or a.get("data-link")
            })

        # FAQs
        faq_questions = syllabus_section.select("div.sectional-faqs > div.html-0")
        for q in faq_questions:
            question = q.get_text(" ", strip=True).replace("Q:", "").strip()
            ans_block = q.find_next_sibling("div", class_="_16f53f")

            if not ans_block:
                continue

            answer = ans_block.select_one(".cmsAContent")
            if answer:
                syllabus_data["faqs"].append({
                    "question": question,
                    "answer": answer.get_text(" ", strip=True)
                })

        data["course_syllabus_section"] = syllabus_data
    # Popular Colleges Section
    # -------------------------
    popular_colleges_section = soup.select_one("div#wikkiContents_chp_section_popularcolleges_0")
    if popular_colleges_section:
        popular_colleges_data = {
            "intro": "",
            "private_colleges": [],
            "government_colleges": [],
            "notes": [],
            "relevant_links": []
        }

        # Intro paragraph
        intro_p = popular_colleges_section.select_one("p")
        if intro_p:
            popular_colleges_data["intro"] = intro_p.get_text(" ", strip=True)

        tables = popular_colleges_section.select("table")

        # ---------- Private Colleges Table ----------
        if len(tables) >= 1:
            for row in tables[0].select("tr")[1:]:
                cols = row.select("td")
                if len(cols) >= 2:
                    link_tag = cols[0].select_one("a")
                    popular_colleges_data["private_colleges"].append({
                        "name": cols[0].get_text(" ", strip=True),
                        "link": link_tag["href"] if link_tag else None,
                        "fees": cols[1].get_text(strip=True)
                    })

        # ---------- Government Colleges Table ----------
        if len(tables) >= 2:
            for row in tables[1].select("tr")[1:]:
                cols = row.select("td")
                if len(cols) >= 2:
                    link_tag = cols[0].select_one("a")
                    popular_colleges_data["government_colleges"].append({
                        "name": cols[0].get_text(" ", strip=True),
                        "link": link_tag["href"] if link_tag else None,
                        "fees": cols[1].get_text(strip=True)
                    })

        # Notes
        for note in popular_colleges_section.select("p em"):
            popular_colleges_data["notes"].append(
                note.get_text(" ", strip=True)
            )

        # Relevant Links
        for a in popular_colleges_section.select("p a"):
            popular_colleges_data["relevant_links"].append({
                "title": a.get_text(strip=True),
                "link": a.get("href")
            })

        data["popular_colleges_section"] = popular_colleges_data
    # -------------------------
    salary_section = soup.select_one("div#wikkiContents_chp_section_salary_0")

    if salary_section:
        salary_data = {
            "intro": "",
            "job_profiles": [],
            "salary_note": "",
            "top_recruiters": [],
            "recruiters_note": "",
            "read_more_links": []
        }

        # Intro paragraph
        intro_p = salary_section.select_one("p")
        if intro_p:
            salary_data["intro"] = intro_p.get_text(" ", strip=True)

        tables = salary_section.select("table")

        # ---------- Job Profile & Salary Table ----------
        if len(tables) >= 1:
            for row in tables[0].select("tr")[1:]:
                cols = row.select("td")
                if len(cols) >= 2:
                    salary_data["job_profiles"].append({
                        "job_profile": cols[0].get_text(strip=True),
                        "average_salary": cols[1].get_text(strip=True)
                    })

        # Salary Note
        salary_note = salary_section.find("p", string=lambda x: x and "AmbitionBox" in x)
        if salary_note:
            salary_data["salary_note"] = salary_note.get_text(" ", strip=True)

        # ---------- Top Recruiters Table ----------
        if len(tables) >= 2:
            recruiter_rows = tables[1].select("tr")[1:]
            for row in recruiter_rows:
                for cell in row.select("td"):
                    recruiter = cell.get_text(strip=True)
                    if recruiter:
                        salary_data["top_recruiters"].append(recruiter)

        # Recruiter Note
        recruiter_note = salary_section.find("p", string=lambda x: x and "various sources" in x)
        if recruiter_note:
            salary_data["recruiters_note"] = recruiter_note.get_text(" ", strip=True)

        # Read More Links
        for a in salary_section.select("p a"):
            salary_data["read_more_links"].append({
                "title": a.get_text(strip=True),
                "link": a.get("href")
            })

        data["career_scope_salary"] = salary_data

    faqs_section = soup.select_one("section#chp_section_faqs")
    faqs_data = []

    if faqs_section:
        faq_blocks = faqs_section.select("div.sectional-faqs div")
        
        i = 0
        while i < len(faq_blocks):
            q_block = faq_blocks[i]
            a_block = faq_blocks[i + 1] if i + 1 < len(faq_blocks) else None

            # Question
            question = ""
            q_text = q_block.get_text(" ", strip=True)
            match = re.match(r"Q[:.\-]?\s*(.*)", q_text, re.I)
            if match:
                question = match.group(1).strip()

            # Answer
            answer = ""
            if a_block:
                content = a_block.select_one("div.cmsAContent")
                if content:
                    answer = content.get_text(" ", strip=True)
                else:
                    answer = a_block.get_text(" ", strip=True)

            if question and answer:
                faqs_data.append({
                    "question": question,
                    "answer": answer
                })

            i += 2

    if faqs_data:
        data["QA"] = faqs_data

    return data



def scrape_shiksha_qa(driver):
    driver.get(PCOMBA_Q_URL)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.post-col[questionid][answerid][type='Q']"))
        )
    except:
        print("No Q&A blocks loaded!")
        return {}

    soup = BeautifulSoup(driver.page_source, "html.parser")

    result = {
        "tag_name": None,
        "description": None,
        "stats": {},
        "questions": []
    }

    # Optional: get tag name & description if exists
    tag_head = soup.select_one("div.tag-head")
    if tag_head:
        tag_name_el = tag_head.select_one("h1.tag-p")
        desc_el = tag_head.select_one("p.tag-bind")
        if tag_name_el:
            result["tag_name"] = tag_name_el.get_text(strip=True)
        if desc_el:
            result["description"] = desc_el.get_text(" ", strip=True)

    # Stats
    stats_cells = soup.select("div.ana-table div.ana-cell")
    stats_keys = ["Questions", "Discussions", "Active Users", "Followers"]
    for key, cell in zip(stats_keys, stats_cells):
        count_tag = cell.select_one("b")
        if count_tag:
            value = count_tag.get("valuecount") or count_tag.get_text(strip=True)
            result["stats"][key] = value

    questions_dict = {}

    for post in soup.select("div.post-col[questionid][answerid][type='Q']"):
        q_text_el = post.select_one("div.dtl-qstn .wikkiContents")
        if not q_text_el:
            continue
        question_text = q_text_el.get_text(" ", strip=True)

        # Tags
        tags = [{"tag_name": a.get_text(strip=True), "tag_url": a.get("href")}
                for a in post.select("div.ana-qstn-block .qstn-row a")]

        # Followers
        followers_el = post.select_one("span.followersCountTextArea")
        followers = int(followers_el.get("valuecount", "0")) if followers_el else 0

        # Author
        author_el = post.select_one("div.avatar-col .avatar-name")
        author_name = author_el.get_text(strip=True) if author_el else None
        author_url = author_el.get("href") if author_el else None

        # Answer text
        answer_el = post.select_one("div.avatar-col .rp-txt .wikkiContents")
        answer_text = answer_el.get_text(" ", strip=True) if answer_el else None

        # Upvotes / downvotes
        upvote_el = post.select_one("a.up-thumb.like-a")
        downvote_el = post.select_one("a.up-thumb.like-d")
        upvotes = int(upvote_el.get_text(strip=True)) if upvote_el and upvote_el.get_text(strip=True).isdigit() else 0
        downvotes = int(downvote_el.get_text(strip=True)) if downvote_el and downvote_el.get_text(strip=True).isdigit() else 0

        # Posted time (if available)
        time_el = post.select_one("div.col-head span")
        posted_time = time_el.get_text(strip=True) if time_el else None

        # Group by question
        if question_text not in questions_dict:
            questions_dict[question_text] = {
                "tags": tags,
                "followers": followers,
                "answers": []
            }
        questions_dict[question_text]["answers"].append({
            "author": {"name": author_name, "profile_url": author_url},
            "answer_text": answer_text,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "posted_time": posted_time
        })

    # Convert dict to list
    for q_text, data in questions_dict.items():
        result["questions"].append({
            "question_text": q_text,
            "tags": data["tags"],
            "followers": data["followers"],
            "answers": data["answers"]
        })

    return result


def scrape_tag_cta_D_block(driver):
    driver.get(PCOMBA_QD_URL)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    result = {
        "questions": []  # store all Q&A and discussion blocks
    }

    # Scrape all Q&A and discussion blocks
    qa_blocks = soup.select("div.post-col[questionid][answerid][type='Q'], div.post-col[questionid][answerid][type='D']")
    for block in qa_blocks:
        block_type = block.get("type", "Q")
        qa_data = {
          
            "posted_time": None,
            "tags": [],
            "question_text": None,
            "followers": 0,
            "views": 0,
            "author": {
                "name": None,
                "profile_url": None,
            },
            "answer_text": None,
        }

        # Posted time
        posted_span = block.select_one("div.col-head span")
        if posted_span:
            qa_data["posted_time"] = posted_span.get_text(strip=True)

        # Tags
        tag_links = block.select("div.ana-qstn-block div.qstn-row a")
        for a in tag_links:
            qa_data["tags"].append({
                "tag_name": a.get_text(strip=True),
                "tag_url": a.get("href")
            })

        # Question / Discussion text
        question_div = block.select_one("div.dtl-qstn a div.wikkiContents")
        if question_div:
            qa_data["question_text"] = question_div.get_text(" ", strip=True)

        # Followers
        followers_span = block.select_one("span.followersCountTextArea, span.follower")
        if followers_span:
            qa_data["followers"] = int(followers_span.get("valuecount", "0"))

        # Views
        views_span = block.select_one("div.right-cl span.viewers-span")
        if views_span:
            views_text = views_span.get_text(strip=True).split()[0].replace("k","000").replace("K","000")
            try:
                qa_data["views"] = int(views_text)
            except:
                qa_data["views"] = views_text

        # Author info
        author_name_a = block.select_one("div.avatar-col a.avatar-name")
        if author_name_a:
            qa_data["author"]["name"] = author_name_a.get_text(strip=True)
            qa_data["author"]["profile_url"] = author_name_a.get("href")

        # Answer / Comment text
        answer_div = block.select_one("div.avatar-col div.wikkiContents")
        if answer_div:
            paragraphs = answer_div.find_all("p")
            if paragraphs:
                qa_data["answer_text"] = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
            else:
                # Sometimes discussion/comment text is direct text without <p>
                qa_data["answer_text"] = answer_div.get_text(" ", strip=True)

        result["questions"].append(qa_data)

    return result



def scrape_mba_colleges():
    driver = create_driver()

      

    try:
       data = {
              "Part_time":{
                   "overviews":scrape_chp_overview_section(driver),
                # "course":scrape_online_mba_overview(driver),
                # "syllabus":scrape_online_mba_syllabus(driver),
                # "JOB":scrape_jobs_overview_section(driver),
                # "addmision":scrape_admission_overview_section(driver),
                "QNA":{
                 "QA_ALL":scrape_shiksha_qa(driver),
                 "QA_D":scrape_tag_cta_D_block(driver),
                },
                
                   }
                }
       
       
        
        # data["overview"] =  overviews
        # data["courses"] = courses

    finally:
        driver.quit()
    
    return data



import time

DATA_FILE =  "distance_mba_data.json"
UPDATE_INTERVAL = 6 * 60 * 60  # 6 hours

def auto_update_scraper():
    # Check last modified time
    # if os.path.exists(DATA_FILE):
    #     last_mod = os.path.getmtime(DATA_FILE)
    #     if time.time() - last_mod < UPDATE_INTERVAL:
    #         print("⏱️ Data is recent, no need to scrape")
    #         return

    print("🔄 Scraping started")
    data = scrape_mba_colleges()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ Data scraped & saved successfully")

if __name__ == "__main__":

    auto_update_scraper()

