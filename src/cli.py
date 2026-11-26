"""command line consultation using an ordered conditional questionnaire."""

from .engine import next_question, run_inference
from .explain import explain_results
from .facts import new_facts
from .frames import new_frame_store
from .questions import apply_answer, available_options, display_options

def ask(question: dict, facts: dict) -> str:
    options = available_options(question, facts)
    labels = display_options(question, facts)
    print(f"\n{question['id']}. {question['prompt']}")
    print(question["reason"])
    for number, option in enumerate(labels, 1):
        print(f"  {number}. {option}")
    while True:
        choice = input("Select an option: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Enter one of the displayed option numbers.")

def run_session(answer_provider=None) -> tuple[dict, dict]:
    """Run an interactive session; an answer provider enables reproducible demos."""
    facts = new_facts()
    frames = new_frame_store()
    asked: set[str] = set()
    print("Home Internet Fault Diagnosis")
    print("The questions are asked in order. Some are skipped when they do not apply.")
    print("Answer only from what you have observed. Choose 'not sure' when appropriate.")

    while True:
        question = next_question(facts, asked, frames=frames)
        if question is None:
            break
        if answer_provider is None:
            try:
                answer = ask(question, facts)
            except EOFError:
                print(
                    "\nInput ended. The consultation has been cancelled "
                    "without producing a diagnosis."
                )
                return facts, {}
        else:
            answer = answer_provider(question)
            options = available_options(question, facts)
            labels = display_options(question, facts)
            if answer not in options:
                raise ValueError(f"Demo answer is not valid for {question['id']} and this connection type: {answer}")
            print(f"\n{question['id']}. {question['prompt']}")
            print(question["reason"])
            for number, option in enumerate(labels, 1):
                print(f"  {number}. {option}")
            answer_index = options.index(answer)
            print(f"Select an option: {answer_index + 1} ({labels[answer_index]})")
        apply_answer(facts, question["id"], answer, frames=frames)
        asked.add(question["id"])

    results = run_inference(facts, frames=frames)
    print("\nEquipment and context recorded: " + frames.describe())
    print("Questions asked: " + ", ".join(sorted(asked, key=lambda q: int(q[1:]))))
    print("\n" + "=" * 60)
    print(explain_results(results, frames.to_facts(facts), frames))
    return facts, results

if __name__ == "__main__":
    run_session()
