"""Hand-written API payloads shaped like each source's real responses.
The JSearch payload includes three fake scam postings used to test the red flags."""
import time

NOW = int(time.time())

SIMPLIFY = [
    {"id": "a1", "title": "Data Analyst Intern", "company_name": "Acme Insurance", "active": True, "is_visible": True,
     "url": "https://acme.wd1.myworkdayjobs.com/careers/job/Lincoln-NE/Data-Analyst-Intern_R1", "locations": ["Lincoln, NE"],
     "date_posted": NOW - 86400, "sponsorship": "Other", "degrees": [], "terms": ["Summer 2027"]},
    {"id": "a2", "title": "Data Science Intern", "company_name": "Defense Co", "active": True, "is_visible": True,
     "url": "https://jobs.lever.co/defense/1", "locations": ["Arlington, VA"], "date_posted": NOW,
     "sponsorship": "U.S. Citizenship is Required", "degrees": [], "terms": ["Summer 2027"]},
    {"id": "a3", "title": "Business Intelligence Intern", "company_name": "Maple Corp", "active": True, "is_visible": True,
     "url": "https://boards.greenhouse.io/maple/jobs/3", "locations": ["Toronto, ON, Canada"], "date_posted": NOW,
     "sponsorship": "Other", "degrees": [], "terms": ["Summer 2027"]},
    {"id": "a4", "title": "Senior Data Analyst", "company_name": "Big Co", "active": True, "is_visible": True,
     "url": "https://x.icims.com/1", "locations": ["Remote in USA"], "date_posted": NOW, "sponsorship": "Other",
     "degrees": [], "terms": []},
    {"id": "a5", "title": "Analytics Intern", "company_name": "Closed Co", "active": False, "is_visible": True,
     "url": "https://x", "locations": ["Omaha, NE"], "date_posted": NOW, "sponsorship": "Other", "degrees": [], "terms": []},
]

JSEARCH = {
    "status": "OK",
    "data": [
        {  # legit
            "job_id": "j1", "job_title": "Junior Data Analyst", "employer_name": "Union Freight",
            "employer_website": "https://www.unionfreight.com", "job_publisher": "LinkedIn",
            "job_apply_link": "https://careers.unionfreight.com/jobs/123", "job_apply_is_direct": True,
            "job_description": "We are looking for a Junior Data Analyst to build dashboards in Tableau and Power BI, "
            "write SQL queries against Snowflake and automate reports in Python. 0-2 years of experience. "
            "Candidates must be authorized to work in the United States. Bilingual Spanish is a plus. " * 2,
            "job_city": "Omaha", "job_state": "NE", "job_country": "US", "job_is_remote": False,
            "job_posted_at_timestamp": NOW - 3600, "job_min_salary": 58000, "job_max_salary": 66000,
            "job_salary_period": "YEAR", "job_employment_type": "FULLTIME",
        },
        {  # scam: check deposit + telegram + personal email
            "job_id": "j2", "job_title": "Remote Data Analyst Intern", "employer_name": "Confidential",
            "job_publisher": "JobBoardX", "job_apply_link": "https://bit.ly/3abcde", "job_apply_is_direct": False,
            "job_description": "Work from home data analyst intern, $45/hr, no interview required! Interviews are "
            "conducted via Telegram. You will receive a check to deposit and purchase your equipment from our "
            "vendor. Send your resume to hr.recruiting.team@gmail.com",
            "job_city": None, "job_state": None, "job_country": "US", "job_is_remote": True,
            "job_posted_at_timestamp": NOW - 7200, "job_employment_type": "INTERN",
        },
        {  # scam: too-good pay, SSN up front
            "job_id": "j3", "job_title": "Entry Level Data Analyst (Remote)", "employer_name": "Global Data Solutions LLC",
            "job_publisher": "JobBoardY", "job_apply_link": "https://apply-globaldatasolutions.net/form",
            "job_description": "No experience necessary. Earn $2,500 per week from home! Urgently hiring. To start "
            "onboarding, your social security number and bank account routing number are required today.",
            "job_country": "US", "job_is_remote": True, "job_posted_at_timestamp": NOW,
            "job_min_salary": 95, "job_max_salary": 120, "job_salary_period": "HOUR", "job_employment_type": "FULLTIME",
        },
        {  # excluded: clearance
            "job_id": "j4", "job_title": "Data Analyst Intern", "employer_name": "Gov Contractor",
            "job_apply_link": "https://govco.wd5.myworkdayjobs.com/x", "job_description": "Must be a U.S. citizen with "
            "the ability to obtain a security clearance. SQL and Excel required. " * 4,
            "job_city": "Bellevue", "job_state": "NE", "job_country": "US", "job_posted_at_timestamp": NOW,
            "job_employment_type": "INTERN",
        },
        {  # caution: no sponsorship
            "job_id": "j5", "job_title": "Business Analyst Intern", "employer_name": "Prairie Mutual",
            "job_apply_link": "https://prairiemutual.wd1.myworkdayjobs.com/x/job/1",
            "job_description": "Help our finance team with Excel and SQL reporting. Hourly wage $22. Applicants must "
            "not now, or in the future, require sponsorship for employment. Graduate students welcome. " * 2,
            "job_city": "Omaha", "job_state": "NE", "job_country": "US", "job_posted_at_timestamp": NOW,
            "job_min_salary": 22, "job_max_salary": 22, "job_salary_period": "HOUR", "job_employment_type": "INTERN",
        },
        {  # excluded: unpaid
            "job_id": "j6", "job_title": "Data Analytics Intern", "employer_name": "Small Nonprofit",
            "job_apply_link": "https://smallnp.bamboohr.com/careers/9",
            "job_description": "This is an unpaid internship for academic credit. Excel and Google Sheets. " * 4,
            "job_city": "Lincoln", "job_state": "NE", "job_country": "US", "job_posted_at_timestamp": NOW,
            "job_employment_type": "INTERN",
        },
        {  # training-for-hire
            "job_id": "j7", "job_title": "Entry Level Data Analyst", "employer_name": "SynergisticIT",
            "job_apply_link": "https://www.synergisticit.com/apply",
            "job_description": "Looking for entry level data analysts. Python, SQL, Tableau. OPT, CPT, H1B welcome. " * 4,
            "job_city": "Dallas", "job_state": "TX", "job_country": "US", "job_posted_at_timestamp": NOW,
            "job_employment_type": "FULLTIME",
        },
    ],
}

ADZUNA = {
    "count": 2,
    "results": [
        {"id": "z1", "title": "<strong>Data</strong> Analyst Intern", "description": "Support analytics team with SQL and "
         "Excel dashboards for our insurance business…", "created": "2026-11-09T15:00:00Z",
         "redirect_url": "https://www.adzuna.com/land/ad/1", "company": {"display_name": "Plains Insurance"},
         "location": {"display_name": "Lincoln, Lancaster County"}, "salary_min": 41600, "salary_max": 45760,
         "salary_is_predicted": "0", "contract_time": "full_time"},
        {"id": "z2", "title": "Data Analyst III", "description": "6+ years of experience", "created": "2026-11-09T15:00:00Z",
         "redirect_url": "https://www.adzuna.com/land/ad/2", "company": {"display_name": "Big Bank"},
         "location": {"display_name": "Chicago, IL"}},
    ],
}

MUSE = {
    "page": 0, "page_count": 1,
    "results": [
        {"id": 101, "name": "Marketing Analytics Intern", "contents": "<p>Analyze campaign data in SQL and Looker. "
         "Paid internship, $24/hour. Open to master's students.</p>" * 3, "publication_date": "2026-11-08T12:00:00Z",
         "locations": [{"name": "Flexible / Remote"}], "levels": [{"name": "Internship", "short_name": "internship"}],
         "refs": {"landing_page": "https://www.themuse.com/jobs/acme/marketing-analytics-intern"},
         "company": {"name": "Brightside Media"}},
    ],
}

GREENHOUSE = {
    "jobs": [
        {"id": 7, "title": "Data Analyst Intern", "updated_at": "2026-11-05T10:00:00-05:00",
         "location": {"name": "Lincoln, Nebraska, United States"},
         "absolute_url": "https://job-boards.greenhouse.io/hudl/jobs/7",
         "content": "&lt;p&gt;Use SQL and Python to analyze sports video data.&lt;/p&gt;" * 6},
        {"id": 8, "title": "Senior Data Analyst", "location": {"name": "Barcelona, Spain"},
         "absolute_url": "https://job-boards.greenhouse.io/hudl/jobs/8", "content": "x"},
    ]
}

LEVER = [
    {"id": "lv1", "text": "Analytics Intern", "hostedUrl": "https://jobs.lever.co/acme/lv1", "createdAt": NOW * 1000,
     "categories": {"location": "Remote - US", "commitment": "Intern", "allLocations": ["Remote - US"]},
     "descriptionPlain": "Build Tableau dashboards and SQL models. " * 10,
     "salaryRange": {"min": 25, "max": 30, "currency": "USD", "interval": "per-hour-wage"}},
]

ASHBY = {
    "jobs": [
        {"id": "as1", "title": "Data Analyst, New Grad", "location": "New York, NY", "secondaryLocations": [],
         "isRemote": False, "descriptionPlain": "SQL, Python, experimentation. " * 15,
         "publishedAt": "2026-11-07T00:00:00.000Z", "employmentType": "FullTime",
         "jobUrl": "https://jobs.ashbyhq.com/acme/as1", "isListed": True},
        {"id": "as2", "title": "Hidden Analyst", "isListed": False},
    ]
}

WORKDAY_LIST = {
    "total": 2,
    "jobPostings": [
        {"title": "Intern - Data Analytics", "externalPath": "/job/Lincoln-NE/Intern---Data-Analytics_R12345",
         "locationsText": "Lincoln, NE", "postedOn": "Posted 2 Days Ago"},
        {"title": "Customer Service Rep", "externalPath": "/job/Remote/CSR_R999", "locationsText": "Remote",
         "postedOn": "Posted Today"},
    ],
}

WORKDAY_DETAIL = {
    "jobPostingInfo": {
        "jobDescription": "<p>Join our analytics team. Use SQL and Power BI. Competitive pay.</p>" * 5,
        "location": "Lincoln, NE", "startDate": "2026-11-08", "timeType": "Full time",
        "externalUrl": "https://nelnet.wd1.myworkdayjobs.com/MyNelnet/job/Lincoln-NE/Intern---Data-Analytics_R12345",
    }
}
