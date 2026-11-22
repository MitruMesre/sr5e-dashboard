use leptos::prelude::*;
use rand::RngExt;

#[component]
fn App() -> impl IntoView {
    let (count, set_count) = signal(0);
    let (number, set_number) = signal(0_i32);
    let (diceroll, set_diceroll) = signal(0_u8);
    let (logs, set_logs) = signal(String::new());

    view! {
        <main>
            <h1>"Hello World!"</h1>
            <section>
                <p>"Count: " {count}</p>
                <button on:click=move |_| set_count.update(|current| *current += 1)>
                    "Add one"
                </button>
                <button on:click=move |_| set_count.update(|current| *current -= 1)>
                    "Subtract one"
                </button>
                <button on:click=move |_| set_count.update(|current| *current = 0)>
                   "Reset"
                </button>
                <button on:click=move |_| set_count.update(|current| *current *= -1)>
                    "Multiply by -1"
                </button>
                <button on:click=move |_| set_count.update(|current| *current *= *current)>
                   "Square"
                </button>
            </section>
            <section>
                <button on:click=move |_| {
                    let roll = rand::rng().random_range(1..=6);
                    set_diceroll.set(roll);
                    set_logs.update(|logs|logs.push_str(format!("\n{roll}").as_str()));
                }>
                   "Roll a Die " {diceroll}
                </button>
            </section>
            <section>
                <textarea readonly rows="8" cols="40" prop:value=move || logs.get()></textarea>
            </section>
            <section>
                <label>
                    "Number "
                    <input
                        type="number"
                        prop:value=move || number.get()
                        on:input=move |event| {
                            if let Ok(parsed) = event_target_value(&event).parse::<i32>() {
                                set_number.set(parsed);
                            }
                        }
                    />
                </label>
                <p>"Number: " {number}</p>
            </section>
        </main>
    }
}

fn main() {
    leptos::mount::mount_to_body(App);
}
