# Normalization

The main recruitment tables follow normalization principles. Attributes hold individual values (1NF). In `user_skills`, proficiency and years of experience describe the combination of user and skill (2NF). An application stores a posting ID. The posting points to the company and category, where their names are stored (3NF).

Two design choices keep extra information for practical use. `applications.status` stores the current state for listing and filtering, and `application_status_history` stores the sequence of changes. `experiences.company_name` keeps the recorded employer name even for external employers or when the optional link to a registered company is cleared. For a linked employer, the recorded name and the company's current name can differ.

