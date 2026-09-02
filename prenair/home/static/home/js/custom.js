document.querySelectorAll(".unique-faq-item").forEach((item) => {
  const question = item.querySelector(".unique-faq-question");
  question.addEventListener("click", () => {
    item.classList.toggle("unique-open");
  });
});
