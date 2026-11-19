use leptos::prelude::*;

#[component]
fn App() -> impl IntoView {
    let (count, set_count) = signal(0);

    view! {
        <h1>"Hello World!"</h1>
        <p>"Count: " {count}</p>
        <button on:click=move |_| set_count.update(|count| *count += 1)>"Add one"</button>
    }
}
fn main() {
    leptos::mount::mount_to_body(App);
}
