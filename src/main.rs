use leptos::prelude::*;

#[component]
fn App() -> impl IntoView {
    let (count, set_count) = signal(0);
    let (number, set_number) = signal(0_i32);

    view! {
        <main>
            <h1>"Hello World!"</h1>
            <section>
                <p>"Count: " {count}</p>
                <button on:click=move |_| set_count.update(|current| *current += 1)>
                    "Add one"
                </button>
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
