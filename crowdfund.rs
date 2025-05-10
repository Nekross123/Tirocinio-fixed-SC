use anchor_lang::prelude::*;

// program ID 
declare_id!("8Bk7qQpQxqBz5XVX3LqV3vbpnNuZLhCnKq316UHThMHV");

#[program]
pub mod crowdfund {
    use super::*;

    // Initializes a new crowdfunding campaign
    pub fn initialize(
        ctx: Context<InitializeCtx>,
        campaign_name: String,
        end_donate_slot: u64,
        goal_in_lamports: u64,
    ) -> Result<()> {
        // Verify the fundraising goal is positive
        require!(goal_in_lamports > 0, CustomError::InvalidAmount);
        // Verify the donation end slot is in the future
        require!(
            Clock::get()?.slot < end_donate_slot,
            CustomError::InvalidEndSlot
        );

        // Set the campaign data
        let campaign_pda = &mut ctx.accounts.campaign_pda;
        campaign_pda.campaign_name = campaign_name;
        campaign_pda.campaign_owner = *ctx.accounts.campaign_owner.key;
        campaign_pda.end_donate_slot = end_donate_slot;
        campaign_pda.goal_in_lamports = goal_in_lamports;
        Ok(())
    }

    // Allows a user to donate to the campaign
    pub fn donate(
        ctx: Context<DonateCtx>,
        _campaign_name: String, // used in seeds but not in the instruction
        donated_lamports: u64,
    ) -> Result<()> {
        let campaign_pda = &mut ctx.accounts.campaign_pda;
        let donor = &mut ctx.accounts.donor;
        let deposit_pda = &mut ctx.accounts.deposit_pda;

        // Verify the donated amount is valid
        require!(donated_lamports > 0, CustomError::InvalidAmount);
        // Verify the campaign is still active
        require!(
            Clock::get()?.slot <= campaign_pda.end_donate_slot,
            CustomError::TimeoutReached
        );

        
        let new_total = deposit_pda.total_donated.checked_add(donated_lamports)
            .ok_or(CustomError::DonationOverflow)?;
        deposit_pda.total_donated = new_total;

        // Build the lamport transfer instruction
        let transfer_instruction = anchor_lang::solana_program::system_instruction::transfer(
            &donor.key(),
            &campaign_pda.key(),
            donated_lamports,
        );

        
        anchor_lang::solana_program::program::invoke(
            &transfer_instruction,
            &[donor.to_account_info(), campaign_pda.to_account_info()],
        )?;

        Ok(())
    }

    // Allows the campaign creator to withdraw funds if the goal has been reached
    pub fn withdraw(
        ctx: Context<WithdrawCtx>,
        _campaign_name: String,
    ) -> Result<()> {
        let campaign_pda = &mut ctx.accounts.campaign_pda;
        let campaign_owner = &mut ctx.accounts.campaign_owner;

        // Verify the campaign has ended
        require!(
            Clock::get()?.slot >= campaign_pda.end_donate_slot,
            CustomError::TimeoutNotReached
        );

        // Calculate the available balance
        let balance = **campaign_pda.to_account_info().try_borrow_mut_lamports()?;
        let rent_exemption =
            Rent::get()?.minimum_balance(campaign_pda.to_account_info().data_len());
        
        require!(balance >= rent_exemption, CustomError::InvalidBalance);

        let lamports_reached = balance - rent_exemption;

        // Verify the goal has been reached
        require!(
            lamports_reached >= campaign_pda.goal_in_lamports,
            CustomError::GoalNotReached
        );

        
        // get balance account PDA
        let pda_lamports = campaign_pda.to_account_info().lamports();
        let owner_lamports = campaign_owner.to_account_info().lamports();

        // overflow control
        let new_owner_lamports = owner_lamports
            .checked_add(pda_lamports)
            .ok_or(CustomError::OverflowError)?;

        // owner update balance
        **campaign_owner.to_account_info().try_borrow_mut_lamports()? = new_owner_lamports;

        // balance pda to 0
        **campaign_pda.to_account_info().try_borrow_mut_lamports()? = 0;

        Ok(())
    }

    // Allows donors to reclaim their funds if the campaign did not reach its goal
    pub fn reclaim(
        ctx: Context<ReclaimCtx>,
        _campaign_name: String,
    ) -> Result<()> {
        let donor = &mut ctx.accounts.donor;
        let campaign_pda = &mut ctx.accounts.campaign_pda;
        let deposit_pda = &mut ctx.accounts.deposit_pda;

        // Verify the campaign has ended
        require!(
            Clock::get()?.slot >= campaign_pda.end_donate_slot,
            CustomError::TimeoutNotReached
        );

        let balance = **campaign_pda.to_account_info().try_borrow_mut_lamports()?;
        let rent_exemption =
            Rent::get()?.minimum_balance(campaign_pda.to_account_info().data_len());
        let lamports_reached = balance - rent_exemption;

        // Allow refunds only if the campaign failed
        require!(
            lamports_reached < campaign_pda.goal_in_lamports,
            CustomError::GoalReached
        );

        // Verify the donor has funds to reclaim
        require!(
            deposit_pda.total_donated > 0,
            CustomError::NoFundsToReclaim
        );
        // Verify the campaign has enough funds to cover the refund
        require!(
            balance >= deposit_pda.total_donated,
            CustomError::InsufficientCampaignFunds
        );

        // Close the deposit_pda account and return the rent to the donor
        **donor.to_account_info().try_borrow_mut_lamports()? += **deposit_pda.to_account_info().try_borrow_mut_lamports()?;
        **deposit_pda.to_account_info().try_borrow_mut_lamports()? = 0;

        // Return the donated amount to the donor
        **donor.to_account_info().try_borrow_mut_lamports()? += deposit_pda.total_donated;
        **campaign_pda.to_account_info().try_borrow_mut_lamports()? -= deposit_pda.total_donated;
        
        // Reset del totale donato
        deposit_pda.total_donated = 0;
        Ok(())
    }
}

// =======================================
// Contexts: define who can call what
// =======================================

// Context for initializing a new campaign
#[derive(Accounts)]
#[instruction(campaign_name: String)]
pub struct InitializeCtx<'info> {
    #[account(mut)]
    pub campaign_owner: Signer<'info>,
    #[account(
        init, 
        payer = campaign_owner, 
        seeds = [campaign_name.as_ref()],
        bump,
        space = 8 + CampaignPDA::INIT_SPACE // Use INIT_SPACE from InitSpace derive
    )]
    pub campaign_pda: Account<'info, CampaignPDA>,
    pub system_program: Program<'info, System>,
}

// Context for donating to a campaign
#[derive(Accounts)]
#[instruction(_campaign_name: String)]
pub struct DonateCtx<'info> {
    #[account(mut)]
    pub donor: Signer<'info>,
    #[account(mut, seeds = [_campaign_name.as_ref()], bump )]
    pub campaign_pda: Account<'info, CampaignPDA>,
    #[account(
        init,
        payer = donor, 
        seeds = ["deposit".as_ref(), _campaign_name.as_ref(), donor.key().as_ref()],
        bump,
        space = 8 + DepositPDA::INIT_SPACE 
    )]
   
    pub deposit_pda: Account<'info, DepositPDA>,
    pub system_program: Program<'info, System>,
}

// Context for withdrawing funds after a successful campaign
#[derive(Accounts)]
#[instruction(_campaign_name: String)]
pub struct WithdrawCtx<'info> {
    #[account(mut)]
    pub campaign_owner: Signer<'info>,
    #[account(
        mut, 
        seeds = [_campaign_name.as_ref()], 
        bump,
        // verify the campaign owner
        constraint = campaign_pda.campaign_owner == campaign_owner.key() @ CustomError::UnauthorizedOwner
    )]
    pub campaign_pda: Account<'info, CampaignPDA>,
}

// Context for reclaiming funds after a failed campaign
#[derive(Accounts)]
#[instruction(_campaign_name: String)]
pub struct ReclaimCtx<'info> {
    #[account(mut)]
    pub donor: Signer<'info>,
    #[account(mut, seeds = [_campaign_name.as_ref()], bump )]
    pub campaign_pda: Account<'info, CampaignPDA>,
    #[account( 
        mut, 
        seeds = ["deposit".as_ref(), _campaign_name.as_ref(), donor.key().as_ref()],
        bump,
    )]
    pub deposit_pda: Account<'info, DepositPDA>,
}

// Campaign account
#[account]
#[derive(InitSpace)]
pub struct CampaignPDA {
    #[max_len(30)]
    pub campaign_name: String,        // Campaign name
    pub campaign_owner: Pubkey,       // Campaign owner
    pub end_donate_slot: u64,         // Donation end slot
    pub goal_in_lamports: u64,        // Goal in lamports
}

// Deposit account for each donor
#[account]
#[derive(InitSpace)]
pub struct DepositPDA {
    pub total_donated: u64, // Total donated by a single user
}

// Custom errors
#[error_code]
pub enum CustomError {
    #[msg("The end slot must be greater than the current slot")]
    InvalidEndSlot,
    #[msg("Invalid amount, must be greater than 0")]
    InvalidAmount,
    #[msg("The timeout slot was reached")]
    TimeoutReached,
    #[msg("The timeout slot was not reached")]
    TimeoutNotReached,
    #[msg("The goal was not reached")]
    GoalNotReached,
    #[msg("The goal was reached")]
    GoalReached,
    #[msg("The account balance is less than the rent exemption")]
    InvalidBalance,
    #[msg("Overflow detected when adding donation amounts")]
    DonationOverflow,
    #[msg("Unauthorized access: only the campaign owner can perform this action")]
    UnauthorizedOwner,
    #[msg("No funds available to reclaim")]
    NoFundsToReclaim,
    #[msg("Insufficient funds in the campaign account")]
    InsufficientCampaignFunds,
    #[msg("Arithmetic overflow occurred during calculation")]
    OverflowError,
}