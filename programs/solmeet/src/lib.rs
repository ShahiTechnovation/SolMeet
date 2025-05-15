use anchor_lang::prelude::*;

declare_id!("SoLMEETsmMaJrjDnqL8ERjV5TuTXYpUz1XoAZzZ2BG");

#[program]
pub mod solmeet {
    use super::*;

    /// Create a new event on-chain
    pub fn create_event(
        ctx: Context<CreateEvent>,
        event_id: String,
        name: String,
        description: String,
        venue: String,
        date: String,
        max_claims: u16,
    ) -> Result<()> {
        let event = &mut ctx.accounts.event;
        let creator = &ctx.accounts.creator;

        // Validate inputs
        require!(event_id.len() <= 16, ErrorCode::EventIdTooLong);
        require!(name.len() <= 50, ErrorCode::NameTooLong);
        require!(description.len() <= 200, ErrorCode::DescriptionTooLong);
        require!(venue.len() <= 100, ErrorCode::VenueTooLong);
        require!(date.len() <= 30, ErrorCode::DateTooLong);
        require!(max_claims > 0, ErrorCode::InvalidMaxClaims);

        event.creator = creator.key();
        event.event_id = event_id;
        event.name = name;
        event.description = description;
        event.venue = venue;
        event.date = date;
        event.max_claims = max_claims;
        event.claims_count = 0;

        msg!("Created event: {}", event.event_id);
        Ok(())
    }

    /// Join an existing event
    pub fn join_event(ctx: Context<JoinEvent>, event_id: String) -> Result<()> {
        let event = &mut ctx.accounts.event;
        let claim = &mut ctx.accounts.claim;
        let attendee = &ctx.accounts.attendee;

        // Verify event exists (this is implicit since we're using the event as an account)
        
        // Check if max claims has been reached
        require!(
            event.claims_count < event.max_claims,
            ErrorCode::MaxClaimsReached
        );

        // Set claim data
        claim.attendee = attendee.key();
        claim.event_id = event_id;
        claim.timestamp = Clock::get()?.unix_timestamp;

        // Increment claims count
        event.claims_count += 1;

        msg!("New attendee joined event: {}", event.event_id);
        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(event_id: String)]
pub struct CreateEvent<'info> {
    #[account(
        init,
        payer = creator,
        space = 8 + Event::space(&event_id),
        seeds = [b"event", event_id.as_bytes()],
        bump
    )]
    pub event: Account<'info, Event>,
    
    #[account(mut)]
    pub creator: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(event_id: String)]
pub struct JoinEvent<'info> {
    #[account(
        mut,
        seeds = [b"event", event_id.as_bytes()],
        bump,
        constraint = event.claims_count < event.max_claims @ ErrorCode::MaxClaimsReached,
    )]
    pub event: Account<'info, Event>,
    
    #[account(
        init,
        payer = attendee,
        space = 8 + Claim::space(&event_id),
        seeds = [b"claim", event_id.as_bytes(), attendee.key().as_ref()],
        bump,
        constraint = event.event_id == event_id @ ErrorCode::EventIdMismatch,
    )]
    pub claim: Account<'info, Claim>,
    
    #[account(mut)]
    pub attendee: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[account]
pub struct Event {
    pub creator: Pubkey,
    pub event_id: String,
    pub name: String,
    pub description: String,
    pub venue: String,
    pub date: String,
    pub max_claims: u16,
    pub claims_count: u16,
}

impl Event {
    fn space(event_id: &str) -> usize {
        // 32 (pubkey) + sizes of strings + 2 + 2 (u16) + padding
        32 + 
        4 + event_id.len() + 
        4 + 50 +  // name: max 50 chars
        4 + 200 + // description: max 200 chars
        4 + 100 + // venue: max 100 chars
        4 + 30 +  // date: max 30 chars
        2 + 2 +   // max_claims and claims_count
        100       // some padding
    }
}

#[account]
pub struct Claim {
    pub attendee: Pubkey,
    pub event_id: String,
    pub timestamp: i64,
}

impl Claim {
    fn space(event_id: &str) -> usize {
        // 32 (pubkey) + size of event_id string + 8 (i64) + padding
        32 + 4 + event_id.len() + 8 + 50
    }
}

#[error_code]
pub enum ErrorCode {
    #[msg("Event ID must be 16 characters or less")]
    EventIdTooLong,
    #[msg("Event name must be 50 characters or less")]
    NameTooLong,
    #[msg("Description must be 200 characters or less")]
    DescriptionTooLong,
    #[msg("Venue must be 100 characters or less")]
    VenueTooLong,
    #[msg("Date must be 30 characters or less")]
    DateTooLong,
    #[msg("Maximum claims must be greater than zero")]
    InvalidMaxClaims,
    #[msg("Maximum number of claims has been reached")]
    MaxClaimsReached,
    #[msg("Event ID mismatch")]
    EventIdMismatch,
    #[msg("Attendee has already joined this event")]
    AlreadyJoined,
}
