# Tests: unit/ mirrors src/ (domain, application); integration/ uses local Supabase and recorded GitHub fixtures.
- Test behaviour through public interfaces. Name tests test_<unit>_<condition>_<expected>.
- Fakes over mocks. No network in unit tests. No sleeps.
- A bug fix starts with a failing test.
