const SCAMS = [
  ["Pay first, seller disappears", "You pay TixSafe, not the seller. If the ticket isn't transferred within 24h, you're refunded automatically."],
  ["Fake or screenshot ticket", "Money stays in escrow until 24h after the show. If the ticket doesn't scan, open a dispute and the funds are frozen."],
  ["Same ticket sold to many buyers", "Each ticket's order reference is fingerprinted. A ticket already on sale can't be listed again, by anyone."],
  ["“Just DuitNow me / WhatsApp me”", "The chat hides phone numbers, links and bank account numbers, and warns both sides. Off-platform payment has no protection."],
  ["Throwaway scammer accounts", "Sellers verify with MyKad; one IC = one account. Two failed deals and selling is suspended."],
  ["Crazy scalper prices", "Resale price is capped at face value + 10%."],
];

export function HowItWorks() {
  return (
    <>
      <h1>How TixSafe protects you</h1>
      <ol className="how">
        <li><strong>Buyer pays TixSafe.</strong> The money is held in escrow; the seller can see it&apos;s there.</li>
        <li><strong>Seller transfers the ticket</strong> through the official ticketing app within 24 hours.</li>
        <li><strong>Buyer goes to the show.</strong> Payment is released 24h after the event, or earlier if the buyer confirms.</li>
        <li><strong>Problem?</strong> Buyer opens a dispute, funds freeze, and support decides using the order timeline and chat.</li>
      </ol>
      <h2>Common scams and how they&apos;re blocked</h2>
      <div className="grid">
        {SCAMS.map(([scam, fix]) => (
          <div className="card" key={scam}>
            <h3>{scam}</h3>
            <p>{fix}</p>
          </div>
        ))}
      </div>
    </>
  );
}
