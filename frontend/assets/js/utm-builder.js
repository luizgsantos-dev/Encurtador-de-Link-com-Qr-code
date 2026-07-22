function buildUrlWithUtm(baseUrl, utmParams) {
  let url;
  try {
    url = new URL(baseUrl);
  } catch {
    return null;
  }

  Object.entries(utmParams).forEach(([key, value]) => {
    if (value) {
      url.searchParams.set(key, value);
    } else {
      url.searchParams.delete(key);
    }
  });

  return url.toString();
}

function readUtmFormValues() {
  return {
    utm_source: document.getElementById("utm-source").value.trim(),
    utm_medium: document.getElementById("utm-medium").value.trim(),
    utm_campaign: document.getElementById("utm-campaign").value.trim(),
    utm_term: document.getElementById("utm-term").value.trim(),
    utm_content: document.getElementById("utm-content").value.trim(),
  };
}

function updateUtmPreview() {
  const preview = document.getElementById("utm-preview");
  const baseUrl = document.getElementById("destination-url").value.trim();

  if (!baseUrl) {
    preview.textContent = "Informe a URL de destino para ver a prévia.";
    return;
  }

  const result = buildUrlWithUtm(baseUrl, readUtmFormValues());
  preview.textContent = result || "URL de destino inválida.";
}

function initUtmBuilder() {
  const watchedFields = [
    "destination-url",
    "utm-source",
    "utm-medium",
    "utm-campaign",
    "utm-term",
    "utm-content",
  ];
  watchedFields.forEach((id) => {
    document.getElementById(id).addEventListener("input", updateUtmPreview);
  });

  document.getElementById("apply-utm-btn").addEventListener("click", () => {
    const baseUrl = document.getElementById("destination-url").value.trim();
    const result = buildUrlWithUtm(baseUrl, readUtmFormValues());
    if (result) {
      document.getElementById("destination-url").value = result;
      updateUtmPreview();
    }
  });
}

function resetUtmFields() {
  ["utm-source", "utm-medium", "utm-campaign", "utm-term", "utm-content"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  document.getElementById("utm-preview").textContent = "A prévia da URL com UTM aparecerá aqui.";
}
