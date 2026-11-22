# UML Class Diagram

`SessionUser` is the class used for signed-in users. The boxes marked `module` show the Python modules and functions involved in sign-in and applications. Database entities and cardinalities are shown in the [ER diagram](ER_DIAGRAM.md).

```mermaid
classDiagram
  class UserMixin
  class SessionUser {
    +int id
    +str first_name
    +str last_name
    +str full_name
    +bool is_active
    +has_role(name) bool
    +check_password(password) bool
  }
  class ApplicationError
  class ValueError
  class AuthRoutes {
    <<module>>
    register()
    login()
  }
  class UserModel {
    <<module>>
    create_account()
    find_user_by_email()
  }
  class SeekerRoutes {
    <<module>>
    apply()
  }
  class CompanyRoutes {
    <<module>>
    applicant_detail()
    hire_candidate()
  }
  class ApplicationService {
    <<module>>
    submit_application()
    update_application_status()
  }
  class ApplicationModel {
    <<module>>
    insert_application()
    update_status()
    insert_status_history()
    insert_notification()
  }
  class InterviewService {
    <<module>>
    schedule_interview()
    change_interview_status()
  }
  class CompanyModel {
    <<module>>
    insert_interview()
    update_interview_status()
  }
  UserMixin <|-- SessionUser
  ValueError <|-- ApplicationError
  AuthRoutes ..> UserModel
  UserModel ..> SessionUser
  SeekerRoutes ..> ApplicationService
  CompanyRoutes ..> ApplicationService
  CompanyRoutes ..> InterviewService
  InterviewService ..> CompanyModel
  InterviewService ..> ApplicationModel
  ApplicationService ..> ApplicationModel
  ApplicationService ..> ApplicationError
```

