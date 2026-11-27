import unittest
from src.askwestern.ingest.clean import clean_html, deduplicate_chunks

class TestCleaning(unittest.TestCase):
    def test_remove_nav(self):
        html = """
            <html>
            <body>
                <nav>Home Admissions Contact</nav>
                <main>
                    <h1>Academic Calendar</h1>
                    <p>Students can view important dates.</p>
                </main>
            </body>
            </html>
        """
        result = clean_html(html) #should ideally remove the <nav> tags

        self.assertIn("Academic Calendar", result)
        self.assertNotIn("Home Admission Contact", result)

    def test_remove_footer(self):
        html = """
            <html>
            <body>
                <main>
                    <p>Tuition information is available online.</p>
                </main>
                <footer>Privacy Policy Copyright Contact</footer>
            </body>
            </html>
        """
        result = clean_html(html) #should ideally remove the <footer> tags

        self.assertIn("Tuition information", result)
        self.assertNotIn("Privacy Policy", result)

    def test_remove_banner(self):
        html = """
            <html>
            <body>
                <div class="site-banner">
                    Welcome to Western
                </div>
                <main>
                    <p>Course registration opens in June.</p>
                </main>
            </body>
            </html>
        """
        result = clean_html(html) #should remove the tag with class="site-banner"

        self.assertIn("Course registration opens in June", result)
        self.assertNotIn("Welcome to Western", result)

    def test_remove_menu_by_class(self):
        html = """
            <html>
                <body>
                    <div class="main-content">
                        <div class="nav-menu">Home About Contact</div>
                        <p>Students can access academic advising.</p>
                    </div>
                </body>
            </html>
        """

        result = clean_html(html) #should remove the tag with class="nav-menu"

        self.assertIn("academic advising", result)
        self.assertNotIn("Home About Contact", result)

    def test_preserve_main_content(self):
        html = """
            <html>
                <body>
                    <header>Western University</header>
                    <main>
                        <h1>Admission Requirements</h1>
                        <p>Applicants must meet program requirements.</p>
                    </main>
                </body>
            </html>
        """

        result = clean_html(html) #should not remove the important text, in this case the <p>

        self.assertIn("Admission Requirements", result)
        self.assertIn("Applicants must meet program requirements", result)

    def test_remove_exact_duplicates(self):
        chunks = [
            "Students can register online.",
            "Academic advising is available.",
            "Students can register online."
        ]

        result = deduplicate_chunks(chunks) #should only keep unique chunks

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "Students can register online.")
        self.assertEqual(result[1], "Academic advising is available.")

    def test_remove_whitespace_duplicates(self):
        chunks = [
            "Course registration opens in June.",
            "Course   registration opens\nin June."
        ]

        result = deduplicate_chunks(chunks) #should remove the white space

        self.assertEqual(len(result), 1)

    def test_preserve_overlapping_chunks(self):
        chunks = [
            "Students can register for courses online.",
            "register for courses online. Academic advising is available."
        ]

        result = deduplicate_chunks(chunks) 

        self.assertEqual(len(result), 2)

    def test_empty_content(self):
        self.assertEqual(clean_html(""), "")
        self.assertEqual(deduplicate_chunks([]), [])
        self.assertEqual(deduplicate_chunks(["", "   "]), [])

    def test_normalize_whitespace(self):
        html = """
            <html>
                <body>
                    <main>
                        <p>Students    can
                        register   online.</p>
                    </main>
                </body>
            </html>
        """

        result = clean_html(html)

        self.assertEqual(result, "Students can register online.")



    def test_remove_calendar_filter_panel(self):
        html = """
            <html>
                <body>
                    <main>
                        <div class="panel panel-default">
                            <div class="panel-heading">
                                <a>
                                    <h4 class="panel-title">Filter By:</h4>
                                </a>
                            </div>
                            <div class="panel-body">
                                <p>Categories</p>
                                <p>Search Clear Filters</p>
                            </div>
                        </div>

                        <div class="calendar-results">
                            <p>January 05, 2026 - Classes Resume</p>
                            <p>January 09, 2026 - Last day to add a course</p>
                        </div>
                    </main>
                </body>
            </html>
        """

        result = clean_html(html) #should now remove any filtering panels from the page

        self.assertNotIn("Filter By:", result)
        self.assertNotIn("Search Clear Filters", result)

        self.assertIn("January 05, 2026", result)
        self.assertIn("January 09, 2026", result)

    
    def test_remove_policy_navigation_sidebar(self):
        html = """
        <html><body>
            <div class="container">
                <div class="col-md-3">
                    <h3 class="policyTitleSideMenu">Policy Categories</h3>
                    <p>Browse by Academic Policy</p>
                    <p>Advanced Policy Search</p>
                </div>
                <div class="col-md-9">
                    <h1>Degree Requirements and Graduation</h1>
                    <p>Students must satisfy graduation requirements.</p>
                </div>
            </div>
        </body></html>
        """

        result = clean_html(html) #should now remove the policy nav sidebar

        self.assertNotIn("Policy Categories", result)
        self.assertNotIn("Advanced Policy Search", result)
        self.assertIn("Degree Requirements and Graduation", result)
        self.assertIn("Students must satisfy graduation requirements", result)

    def test_remove_course_search_button(self):
        html = """
            <html><body>
                <main>
                    <div class="text-center">
                        <a class="btn btn-info novecento">
                            Or Search By Courses
                        </a>
                    </div>
                    <p>Enrolment in each course is limited.</p>
                </main>     
            </body></html>
        """

        result = clean_html(html) #should now remove the course search button

        self.assertNotIn("Or Search By Courses", result)
        self.assertIn("Enrolment in each course is limited", result)

    def test_remove_faculty_staff_search(self):
        html = """
            <html><body>
                <section id="hidden-ribbon">
                    <div id="ribbon-directory">
                        <div class="ind-search">
                            <p>Faculty/Staff Search</p>
                            <p>First Name Last Name Department/Unit Search</p>
                        </div>
                    </div>
                </section>
                <main>
                    <h1>Arts & Humanities Academic Advising</h1>
                    <p>Academic advisors help students with course registration.</p>
                </main>
            </body></html>
        """

        result = clean_html(html) #should now remove the faulty search bar

        self.assertNotIn("Faculty/Staff Search", result)
        self.assertNotIn("Department/Unit Search", result)
        self.assertIn("Arts & Humanities Academic Advising", result)
        self.assertIn("Academic advisors help students", result)


if __name__ == "__main__":
    unittest.main()

        