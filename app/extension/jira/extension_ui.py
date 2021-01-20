import random

from selenium.webdriver.common.by import By

from selenium_ui.base_page import BasePage
from selenium_ui.conftest import print_timing
from util.conf import JIRA_SETTINGS
from time import sleep;

def app_specific_action(driver, datasets):
    page = BasePage(driver)
    issue_key = ''
    if datasets['custom_issues']:
        app_specific_issue = random.choice(datasets['custom_issues'])
        issue_key = app_specific_issue[0]

    @print_timing("selenium_app_custom_action")
    def measure():

        @print_timing("selenium_app_custom_action:update_custom_field")
        def sub_measure():
            # View issue
            page.go_to_url(f"{JIRA_SETTINGS.server_url}/browse/{issue_key}")

            # Make sure custom field is property rendered
            selector = "#customfield_11100-val .confluence-fields-values li[data-value]" # Custom field values selector
            page.wait_until_visible((By.CSS_SELECTOR, selector))
            def countValues():
                return driver.execute_script("return $('" + selector + "').length")
            count0 = countValues() # number of values in a field

            # Update issue
            page.go_to_url(f"{JIRA_SETTINGS.server_url}/secure/EditIssue!default.jspa?key={issue_key}")
            page.wait_until_visible((By.ID, "customfield_11100"))

            sleep(2) # Takes some time to init AUI select2

            # Scroll to Clients custom field, open the dropdown, and add a new option
            driver.execute_async_script("""
                const done = arguments[0];

                if (AJS.$('#resolution').val() === '-1') {
                    AJS.$('#resolution').val('10030'); // set to Done
                }

                [...document.querySelectorAll('.field-group label')]
                .filter(label => label.textContent === 'Clients')
                .forEach(label => {
                    label.scrollIntoView();
                    const $input = AJS.$(label.parentElement).find('input.select2-offscreen');
                    $input.auiSelect2('open');

                    setTimeout(() => {
                        function pressArrowDown($elt) {
                            const evt = AJS.$.Event('keydown');
                            evt.which = 40;
                            $elt.trigger(evt);
                        }
                        function pressEnter($elt) {
                            const evt = AJS.$.Event('keydown');
                            evt.which = 13;
                            $elt.trigger(evt);
                        }
                        const $elt = AJS.$('.select2-input.select2-focused').focus();
                        pressArrowDown($elt);
                        pressArrowDown($elt);
                        pressArrowDown($elt);
                        pressArrowDown($elt);
                        pressEnter($elt)
                        setTimeout(() => done(), 100);
                    }, 1000);
                });
            """)

            # Submit the form
            page.wait_until_clickable((By.ID, 'issue-edit-submit')).click()
            sleep(1)

            page.wait_until_visible((By.CSS_SELECTOR, selector))
            count1 = countValues()
            # print(issue_key, count0, count1)
            assert count0 + 1 == count1

        sub_measure()
    measure()
